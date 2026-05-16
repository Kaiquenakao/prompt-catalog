package main

import (
	"context"
	"encoding/json"
	"fmt"
	"os"
	"strings"
	"time"

	"github.com/aws/aws-lambda-go/events"
	"github.com/aws/aws-lambda-go/lambda"
	"github.com/aws/aws-sdk-go-v2/aws"
	"github.com/aws/aws-sdk-go-v2/config"
	"github.com/aws/aws-sdk-go-v2/feature/dynamodb/attributevalue"
	"github.com/aws/aws-sdk-go-v2/service/bedrockruntime"
	"github.com/aws/aws-sdk-go-v2/service/dynamodb"
	"github.com/google/uuid"
)

var (
	bedrockClient *bedrockruntime.Client
	dynamoClient  *dynamodb.Client
	historyTable  = os.Getenv("HISTORY_TABLE")
)

func init() {
	cfg, _ := config.LoadDefaultConfig(context.Background(),
		config.WithRegion(os.Getenv("REGION")),
	)
	bedrockClient = bedrockruntime.NewFromConfig(cfg)
	dynamoClient = dynamodb.NewFromConfig(cfg)
}

// ── structs ───────────────────────────────────────────────

type RunRequest struct {
	PromptName   string  `json:"prompt_name"`
	SystemPrompt string  `json:"system_prompt"`
	UserMessage  string  `json:"user_message"`
	ModelID      string  `json:"model_id"`
	Temperature  float64 `json:"temperature"`
	MaxTokens    int     `json:"max_tokens"`
	SessionID    string  `json:"session_id"`
}

type ExecutionRecord struct {
	ExecutionID  string  `dynamodbav:"execution_id"`
	SessionID    string  `dynamodbav:"session_id"`
	PromptName   string  `dynamodbav:"prompt_name"`
	SystemPrompt string  `dynamodbav:"system_prompt"`
	UserMessage  string  `dynamodbav:"user_message"`
	ModelID      string  `dynamodbav:"model_id"`
	Temperature  float64 `dynamodbav:"temperature"`
	MaxTokens    int     `dynamodbav:"max_tokens"`
	Status       string  `dynamodbav:"status"` // pending | done | error
	Output       string  `dynamodbav:"output"`
	InputTokens  int     `dynamodbav:"input_tokens"`
	OutputTokens int     `dynamodbav:"output_tokens"`
	LatencyMs    int64   `dynamodbav:"latency_ms"`
	CreatedAt    string  `dynamodbav:"created_at"`
	UpdatedAt    string  `dynamodbav:"updated_at"`
	TTL          int64   `dynamodbav:"ttl"` // expira em 30 dias
}

type BedrockRequest struct {
	AnthropicVersion string    `json:"anthropic_version"`
	MaxTokens        int       `json:"max_tokens"`
	Temperature      float64   `json:"temperature"`
	System           string    `json:"system"`
	Messages         []Message `json:"messages"`
}

type Message struct {
	Role    string `json:"role"`
	Content string `json:"content"`
}

type BedrockResponse struct {
	Content []struct {
		Text string `json:"text"`
	} `json:"content"`
	Usage struct {
		InputTokens  int `json:"input_tokens"`
		OutputTokens int `json:"output_tokens"`
	} `json:"usage"`
}

// ── handler ───────────────────────────────────────────────

func handler(ctx context.Context, req events.APIGatewayProxyRequest) (events.APIGatewayProxyResponse, error) {
	var body RunRequest
	if err := json.Unmarshal([]byte(req.Body), &body); err != nil {
		return errorResponse(400, "body inválido: "+err.Error()), nil
	}

	if body.SystemPrompt == "" || body.ModelID == "" || body.SessionID == "" {
		return errorResponse(400, "system_prompt, model_id e session_id são obrigatórios"), nil
	}

	executionID := uuid.New().String()
	now := time.Now().UTC()

	// salva como "pending" imediatamente
	record := ExecutionRecord{
		ExecutionID:  executionID,
		SessionID:    body.SessionID,
		PromptName:   body.PromptName,
		SystemPrompt: body.SystemPrompt,
		UserMessage:  body.UserMessage,
		ModelID:      body.ModelID,
		Temperature:  body.Temperature,
		MaxTokens:    body.MaxTokens,
		Status:       "pending",
		CreatedAt:    now.Format(time.RFC3339),
		UpdatedAt:    now.Format(time.RFC3339),
		TTL:          now.Add(30 * 24 * time.Hour).Unix(),
	}

	if err := saveRecord(ctx, record); err != nil {
		return errorResponse(500, "erro ao salvar execução: "+err.Error()), nil
	}

	// executa inferência
	start := time.Now()
	output, inputTokens, outputTokens, inferErr := invokeModel(ctx, body)
	latency := time.Since(start).Milliseconds()

	// atualiza com resultado
	record.UpdatedAt = time.Now().UTC().Format(time.RFC3339)
	record.LatencyMs = latency
	record.InputTokens = inputTokens
	record.OutputTokens = outputTokens

	if inferErr != nil {
		record.Status = "error"
		record.Output = inferErr.Error()
	} else {
		record.Status = "done"
		record.Output = output
	}

	if err := saveRecord(ctx, record); err != nil {
		return errorResponse(500, "erro ao atualizar execução: "+err.Error()), nil
	}

	respBody, _ := json.Marshal(map[string]interface{}{
		"execution_id":  executionID,
		"status":        record.Status,
		"output":        record.Output,
		"input_tokens":  inputTokens,
		"output_tokens": outputTokens,
		"latency_ms":    latency,
	})

	return events.APIGatewayProxyResponse{
		StatusCode: 200,
		Headers: map[string]string{
			"Content-Type":                "application/json",
			"Access-Control-Allow-Origin": "*",
		},
		Body: string(respBody),
	}, nil
}

// ── bedrock ───────────────────────────────────────────────

func invokeModel(ctx context.Context, req RunRequest) (string, int, int, error) {
	userMsg := req.UserMessage
	if userMsg == "" {
		userMsg = "Execute o prompt conforme instruído."
	}

	payload := BedrockRequest{
		AnthropicVersion: "bedrock-2023-05-31",
		MaxTokens:        req.MaxTokens,
		Temperature:      req.Temperature,
		System:           req.SystemPrompt,
		Messages: []Message{
			{Role: "user", Content: userMsg},
		},
	}

	payloadBytes, _ := json.Marshal(payload)

	// modelos novos exigem cross-region inference profile com prefixo us.
	modelID := req.ModelID
	if !strings.HasPrefix(modelID, "us.") && !strings.HasPrefix(modelID, "eu.") && !strings.HasPrefix(modelID, "arn:") {
		modelID = "us." + modelID
	}

	resp, err := bedrockClient.InvokeModel(ctx, &bedrockruntime.InvokeModelInput{
		ModelId:     aws.String(modelID),
		Body:        payloadBytes,
		ContentType: aws.String("application/json"),
	})
	if err != nil {
		return "", 0, 0, fmt.Errorf("bedrock error: %w", err)
	}

	var bedrockResp BedrockResponse
	if err := json.Unmarshal(resp.Body, &bedrockResp); err != nil {
		return "", 0, 0, fmt.Errorf("parse error: %w", err)
	}

	output := ""
	if len(bedrockResp.Content) > 0 {
		output = bedrockResp.Content[0].Text
	}

	return output, bedrockResp.Usage.InputTokens, bedrockResp.Usage.OutputTokens, nil
}

// ── dynamodb ──────────────────────────────────────────────

func saveRecord(ctx context.Context, record ExecutionRecord) error {
	item, err := attributevalue.MarshalMap(record)
	if err != nil {
		return err
	}
	_, err = dynamoClient.PutItem(ctx, &dynamodb.PutItemInput{
		TableName: aws.String(historyTable),
		Item:      item,
	})
	return err
}

func errorResponse(code int, msg string) events.APIGatewayProxyResponse {
	body, _ := json.Marshal(map[string]string{"error": msg})
	return events.APIGatewayProxyResponse{
		StatusCode: code,
		Headers:    map[string]string{"Content-Type": "application/json"},
		Body:       string(body),
	}
}

func main() {
	lambda.Start(handler)
}
