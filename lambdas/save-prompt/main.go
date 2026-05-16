package main

import (
	"context"
	"encoding/json"
	"fmt"
	"os"
	"strconv"
	"strings"
	"time"

	"github.com/aws/aws-lambda-go/events"
	"github.com/aws/aws-lambda-go/lambda"
	"github.com/aws/aws-sdk-go-v2/aws"
	"github.com/aws/aws-sdk-go-v2/config"
	"github.com/aws/aws-sdk-go-v2/feature/dynamodb/attributevalue"
	"github.com/aws/aws-sdk-go-v2/service/dynamodb"
	"github.com/aws/aws-sdk-go-v2/service/dynamodb/types"
)

var (
	dynamoClient *dynamodb.Client
	promptsTable = os.Getenv("PROMPTS_TABLE")
)

func init() {
	cfg, _ := config.LoadDefaultConfig(context.Background(),
		config.WithRegion(os.Getenv("REGION")),
	)
	dynamoClient = dynamodb.NewFromConfig(cfg)
}

// ── structs ───────────────────────────────────────────────

type SaveRequest struct {
	PromptName   string   `json:"prompt_name"`
	SystemPrompt string   `json:"system_prompt"`
	Description  string   `json:"description"`
	Tags         []string `json:"tags"`
	ModelID      string   `json:"model_id"`
	Temperature  float64  `json:"temperature"`
	MaxTokens    int      `json:"max_tokens"`
	SessionID    string   `json:"session_id"`
	IsActive     bool     `json:"is_active"`
}

type PromptRecord struct {
	PromptID     string   `dynamodbav:"prompt_id"     json:"prompt_id"`
	Version      string   `dynamodbav:"version"       json:"version"`
	VersionNum   int      `dynamodbav:"version_num"   json:"version_num"`
	SystemPrompt string   `dynamodbav:"system_prompt" json:"system_prompt"`
	Description  string   `dynamodbav:"description"   json:"description"`
	Tags         []string `dynamodbav:"tags"          json:"tags"`
	ModelID      string   `dynamodbav:"model_id"      json:"model_id"`
	Temperature  float64  `dynamodbav:"temperature"   json:"temperature"`
	MaxTokens    int      `dynamodbav:"max_tokens"    json:"max_tokens"`
	Status       string   `dynamodbav:"status"        json:"status"`
	IsActive     bool     `dynamodbav:"is_active"     json:"is_active"`
	DeployedBy   string   `dynamodbav:"deployed_by"   json:"deployed_by"`
	CreatedAt    string   `dynamodbav:"created_at"    json:"created_at"`
}

// ── handler ───────────────────────────────────────────────

func handler(ctx context.Context, req events.APIGatewayProxyRequest) (events.APIGatewayProxyResponse, error) {
	// GET /prompts/{prompt_id} — busca versões existentes
	if promptID, ok := req.PathParameters["prompt_id"]; ok {
		return getVersions(ctx, promptID)
	}

	// POST /prompts — salva novo prompt/versão
	var body SaveRequest
	if err := json.Unmarshal([]byte(req.Body), &body); err != nil {
		return errorResponse(400, "body inválido: "+err.Error()), nil
	}
	if body.PromptName == "" || body.SystemPrompt == "" {
		return errorResponse(400, "prompt_name e system_prompt são obrigatórios"), nil
	}

	return savePrompt(ctx, body)
}

// getVersions — lista todas as versões de um prompt
func getVersions(ctx context.Context, promptID string) (events.APIGatewayProxyResponse, error) {
	result, err := dynamoClient.Query(ctx, &dynamodb.QueryInput{
		TableName:              aws.String(promptsTable),
		KeyConditionExpression: aws.String("prompt_id = :pid"),
		ExpressionAttributeValues: map[string]types.AttributeValue{
			":pid": &types.AttributeValueMemberS{Value: promptID},
		},
		ScanIndexForward: aws.Bool(false), // versão mais recente primeiro
	})
	if err != nil {
		return errorResponse(500, "erro ao buscar versões: "+err.Error()), nil
	}

	records := make([]PromptRecord, 0)
	attributevalue.UnmarshalListOfMaps(result.Items, &records)

	body, _ := json.Marshal(map[string]interface{}{
		"prompt_id": promptID,
		"versions":  records,
		"count":     len(records),
	})
	return successResponse(string(body)), nil
}

// savePrompt — cria nova versão, desativa a anterior se is_active=true
func savePrompt(ctx context.Context, req SaveRequest) (events.APIGatewayProxyResponse, error) {
	// busca versões existentes para determinar próxima versão
	existing, err := dynamoClient.Query(ctx, &dynamodb.QueryInput{
		TableName:              aws.String(promptsTable),
		KeyConditionExpression: aws.String("prompt_id = :pid"),
		ExpressionAttributeValues: map[string]types.AttributeValue{
			":pid": &types.AttributeValueMemberS{Value: req.PromptName},
		},
	})
	if err != nil {
		return errorResponse(500, "erro ao verificar versões: "+err.Error()), nil
	}

	// calcula próxima versão
	nextVersionNum := 1
	if existing.Count > 0 {
		for _, item := range existing.Items {
			var r PromptRecord
			if err := attributevalue.UnmarshalMap(item, &r); err == nil {
				if r.VersionNum >= nextVersionNum {
					nextVersionNum = r.VersionNum + 1
				}
			}
		}
	}

	isFirstVersion := nextVersionNum == 1
	versionStr := fmt.Sprintf("v%d", nextVersionNum)

	// se is_active=true, desativa versões anteriores
	if req.IsActive && !isFirstVersion {
		for _, item := range existing.Items {
			var r PromptRecord
			if err := attributevalue.UnmarshalMap(item, &r); err == nil && r.IsActive {
				dynamoClient.UpdateItem(ctx, &dynamodb.UpdateItemInput{
					TableName: aws.String(promptsTable),
					Key: map[string]types.AttributeValue{
						"prompt_id": &types.AttributeValueMemberS{Value: r.PromptID},
						"version":   &types.AttributeValueMemberS{Value: r.Version},
					},
					UpdateExpression: aws.String("SET is_active = :f"),
					ExpressionAttributeValues: map[string]types.AttributeValue{
						":f": &types.AttributeValueMemberBOOL{Value: false},
					},
				})
			}
		}
	}

	// salva nova versão
	record := PromptRecord{
		PromptID:     req.PromptName,
		Version:      versionStr,
		VersionNum:   nextVersionNum,
		SystemPrompt: req.SystemPrompt,
		Description:  req.Description,
		Tags:         req.Tags,
		ModelID:      req.ModelID,
		Temperature:  req.Temperature,
		MaxTokens:    req.MaxTokens,
		Status:       "prod",
		IsActive:     req.IsActive,
		DeployedBy:   req.SessionID,
		CreatedAt:    time.Now().UTC().Format(time.RFC3339),
	}

	item, err := attributevalue.MarshalMap(record)
	if err != nil {
		return errorResponse(500, "erro ao serializar: "+err.Error()), nil
	}
	if _, err := dynamoClient.PutItem(ctx, &dynamodb.PutItemInput{
		TableName: aws.String(promptsTable),
		Item:      item,
	}); err != nil {
		return errorResponse(500, "erro ao salvar: "+err.Error()), nil
	}

	body, _ := json.Marshal(map[string]interface{}{
		"prompt_id":       record.PromptID,
		"version":         versionStr,
		"version_num":     nextVersionNum,
		"is_first_version": isFirstVersion,
		"is_active":       req.IsActive,
		"status":          "prod",
	})
	return successResponse(string(body)), nil
}

// ── helpers ───────────────────────────────────────────────

func nextVersion(items []map[string]types.AttributeValue) int {
	max := 0
	for _, item := range items {
		if v, ok := item["version"]; ok {
			if mv, ok := v.(*types.AttributeValueMemberS); ok {
				n, _ := strconv.Atoi(strings.TrimPrefix(mv.Value, "v"))
				if n > max {
					max = n
				}
			}
		}
	}
	return max + 1
}

func successResponse(body string) events.APIGatewayProxyResponse {
	return events.APIGatewayProxyResponse{
		StatusCode: 200,
		Headers: map[string]string{
			"Content-Type":                "application/json",
			"Access-Control-Allow-Origin": "*",
		},
		Body: body,
	}
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
