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
	promptsTable = os.Getenv("PROMPTS_TABLE")
)

func init() {
	cfg, _ := config.LoadDefaultConfig(context.Background(),
		config.WithRegion(os.Getenv("REGION")),
	)
	dynamoClient = dynamodb.NewFromConfig(cfg)
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

func handler(ctx context.Context, req events.APIGatewayProxyRequest) (events.APIGatewayProxyResponse, error) {
	// GET /prompts/{prompt_id} — todas as versões de um prompt específico
	if promptID, ok := req.PathParameters["prompt_id"]; ok {
		return getVersions(ctx, promptID)
	}

	// GET /prompts — lista o mais recente de cada prompt
	return listAllPrompts(ctx)
}

// listAllPrompts — retorna a versão mais recente de cada prompt_id
func listAllPrompts(ctx context.Context) (events.APIGatewayProxyResponse, error) {
	result, err := dynamoClient.Scan(ctx, &dynamodb.ScanInput{
		TableName: aws.String(promptsTable),
	})
	if err != nil {
		return errorResponse(500, "erro ao listar prompts: "+err.Error()), nil
	}

	records := make([]PromptRecord, 0)
	if err := attributevalue.UnmarshalListOfMaps(result.Items, &records); err != nil {
		return errorResponse(500, "erro ao deserializar: "+err.Error()), nil
	}

	// agrupa por prompt_id, mantém apenas a versão mais recente
	latest := make(map[string]PromptRecord)
	for _, r := range records {
		if existing, ok := latest[r.PromptID]; !ok || r.VersionNum > existing.VersionNum {
			latest[r.PromptID] = r
		}
	}

	list := make([]PromptRecord, 0, len(latest))
	for _, r := range latest {
		list = append(list, r)
	}

	body, _ := json.Marshal(map[string]interface{}{
		"prompts": list,
		"count":   len(list),
	})
	return successResponse(string(body)), nil
}

// getVersions — todas as versões de um prompt_id, ordenadas da mais recente
func getVersions(ctx context.Context, promptID string) (events.APIGatewayProxyResponse, error) {
	result, err := dynamoClient.Query(ctx, &dynamodb.QueryInput{
		TableName:              aws.String(promptsTable),
		KeyConditionExpression: aws.String("prompt_id = :pid"),
		ExpressionAttributeValues: map[string]types.AttributeValue{
			":pid": &types.AttributeValueMemberS{Value: promptID},
		},
		ScanIndexForward: aws.Bool(false),
	})
	if err != nil {
		return errorResponse(500, "erro ao buscar versões: "+err.Error()), nil
	}

	records := make([]PromptRecord, 0)
	if err := attributevalue.UnmarshalListOfMaps(result.Items, &records); err != nil {
		return errorResponse(500, "erro ao deserializar: "+err.Error()), nil
	}

	body, _ := json.Marshal(map[string]interface{}{
		"prompt_id": promptID,
		"versions":  records,
		"count":     len(records),
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
