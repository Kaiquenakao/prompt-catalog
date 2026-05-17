package main

import (
	"context"
	"encoding/json"
	"os"

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
	historyTable = os.Getenv("HISTORY_TABLE")
)

func init() {
	cfg, _ := config.LoadDefaultConfig(context.Background(),
		config.WithRegion(os.Getenv("REGION")),
	)
	dynamoClient = dynamodb.NewFromConfig(cfg)
}

type ExecutionRecord struct {
	ExecutionID   string  `dynamodbav:"execution_id"  json:"execution_id"`
	SessionID     string  `dynamodbav:"session_id"    json:"session_id"`
	PromptName    string  `dynamodbav:"prompt_name"   json:"prompt_name"`
	PromptVersion string  `dynamodbav:"prompt_version" json:"prompt_version"`
	RunType       string  `dynamodbav:"run_type"      json:"run_type"`
	SystemPrompt  string  `dynamodbav:"system_prompt" json:"system_prompt"`
	UserMessage   string  `dynamodbav:"user_message"  json:"user_message"`
	ModelID       string  `dynamodbav:"model_id"      json:"model_id"`
	Temperature   float64 `dynamodbav:"temperature"   json:"temperature"`
	MaxTokens     int     `dynamodbav:"max_tokens"    json:"max_tokens"`
	Status        string  `dynamodbav:"status"        json:"status"`
	Output        string  `dynamodbav:"output"        json:"output"`
	InputTokens   int     `dynamodbav:"input_tokens"  json:"input_tokens"`
	OutputTokens  int     `dynamodbav:"output_tokens" json:"output_tokens"`
	LatencyMs     int64   `dynamodbav:"latency_ms"    json:"latency_ms"`
	CreatedAt     string  `dynamodbav:"created_at"    json:"created_at"`
}

func handler(ctx context.Context, req events.APIGatewayProxyRequest) (events.APIGatewayProxyResponse, error) {
	// GET /executions/{execution_id} — polling
	if execID, ok := req.PathParameters["execution_id"]; ok {
		return getExecution(ctx, execID)
	}

	// GET /executions?prompt_name=xxx&run_type=playground — histórico do prompt
	if promptName := req.QueryStringParameters["prompt_name"]; promptName != "" {
		runType := req.QueryStringParameters["run_type"] // playground | production | "" (todos)
		return listByPrompt(ctx, promptName, runType)
	}

	// GET /executions?session_id=xxx — histórico da sessão (playground)
	sessionID := req.QueryStringParameters["session_id"]
	if sessionID == "" {
		return errorResponse(400, "session_id ou prompt_name é obrigatório"), nil
	}
	return listExecutions(ctx, sessionID)
}

// getExecution — busca execução por ID (usado no polling)
func getExecution(ctx context.Context, executionID string) (events.APIGatewayProxyResponse, error) {
	result, err := dynamoClient.GetItem(ctx, &dynamodb.GetItemInput{
		TableName: aws.String(historyTable),
		Key: map[string]types.AttributeValue{
			"execution_id": &types.AttributeValueMemberS{Value: executionID},
		},
	})
	if err != nil {
		return errorResponse(500, "erro ao buscar execução: "+err.Error()), nil
	}
	if result.Item == nil {
		return errorResponse(404, "execução não encontrada"), nil
	}

	var record ExecutionRecord
	if err := attributevalue.UnmarshalMap(result.Item, &record); err != nil {
		return errorResponse(500, "erro ao deserializar: "+err.Error()), nil
	}

	body, _ := json.Marshal(record)
	return successResponse(string(body)), nil
}

// listByPrompt — histórico por prompt_name com filtro opcional de run_type
func listByPrompt(ctx context.Context, promptName string, runType string) (events.APIGatewayProxyResponse, error) {
	input := &dynamodb.QueryInput{
		TableName:              aws.String(historyTable),
		IndexName:              aws.String("prompt-index"),
		KeyConditionExpression: aws.String("prompt_name = :pn"),
		ExpressionAttributeValues: map[string]types.AttributeValue{
			":pn": &types.AttributeValueMemberS{Value: promptName},
		},
		ScanIndexForward: aws.Bool(false),
		Limit:            aws.Int32(100),
	}

	// filtra por run_type se informado
	if runType != "" {
		input.FilterExpression = aws.String("run_type = :rt")
		input.ExpressionAttributeValues[":rt"] = &types.AttributeValueMemberS{Value: runType}
	}

	result, err := dynamoClient.Query(ctx, input)
	if err != nil {
		return errorResponse(500, "erro ao listar histórico: "+err.Error()), nil
	}

	records := make([]ExecutionRecord, 0)
	if err := attributevalue.UnmarshalListOfMaps(result.Items, &records); err != nil {
		return errorResponse(500, "erro ao deserializar: "+err.Error()), nil
	}

	body, _ := json.Marshal(map[string]interface{}{
		"executions": records,
		"count":      len(records),
	})
	return successResponse(string(body)), nil
}

// listExecutions — histórico por session_id
func listExecutions(ctx context.Context, sessionID string) (events.APIGatewayProxyResponse, error) {
	result, err := dynamoClient.Query(ctx, &dynamodb.QueryInput{
		TableName:              aws.String(historyTable),
		IndexName:              aws.String("session-index"),
		KeyConditionExpression: aws.String("session_id = :sid"),
		ExpressionAttributeValues: map[string]types.AttributeValue{
			":sid": &types.AttributeValueMemberS{Value: sessionID},
		},
		ScanIndexForward: aws.Bool(false), // mais recente primeiro
		Limit:            aws.Int32(50),
	})
	if err != nil {
		return errorResponse(500, "erro ao listar histórico: "+err.Error()), nil
	}

	records := make([]ExecutionRecord, 0)
	if err := attributevalue.UnmarshalListOfMaps(result.Items, &records); err != nil {
		return errorResponse(500, "erro ao deserializar: "+err.Error()), nil
	}

	body, _ := json.Marshal(map[string]interface{}{
		"executions": records,
		"count":      len(records),
	})
	return successResponse(string(body)), nil
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
