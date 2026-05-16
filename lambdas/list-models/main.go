package main

import (
	"context"
	"encoding/json"
	"os"

	"github.com/aws/aws-lambda-go/events"
	"github.com/aws/aws-lambda-go/lambda"
	"github.com/aws/aws-sdk-go-v2/config"
	"github.com/aws/aws-sdk-go-v2/service/bedrock"
)

type Model struct {
	ID   string `json:"id"`
	Name string `json:"name"`
}

type Response struct {
	Models []Model `json:"models"`
}

func handler(ctx context.Context, _ events.APIGatewayProxyRequest) (events.APIGatewayProxyResponse, error) {
	region := os.Getenv("REGION")
	if region == "" {
		region = "us-east-1"
	}

	cfg, err := config.LoadDefaultConfig(ctx, config.WithRegion(region))
	if err != nil {
		return errorResponse(500, "erro ao carregar config AWS: "+err.Error()), nil
	}

	client := bedrock.NewFromConfig(cfg)

	output, err := client.ListFoundationModels(ctx, &bedrock.ListFoundationModelsInput{
		ByProvider:       strPtr("Anthropic"),
		ByOutputModality: "TEXT",
	})
	if err != nil {
		return errorResponse(500, "erro ao listar modelos: "+err.Error()), nil
	}

	var models []Model
	for _, m := range output.ModelSummaries {
		if m.ModelLifecycle != nil && string(m.ModelLifecycle.Status) == "ACTIVE" {
			models = append(models, Model{
				ID:   *m.ModelId,
				Name: *m.ModelName,
			})
		}
	}

	if models == nil {
		models = []Model{}
	}

	body, _ := json.Marshal(Response{Models: models})

	return events.APIGatewayProxyResponse{
		StatusCode: 200,
		Headers: map[string]string{
			"Content-Type":                "application/json",
			"Access-Control-Allow-Origin": "*",
		},
		Body: string(body),
	}, nil
}

func errorResponse(code int, msg string) events.APIGatewayProxyResponse {
	body, _ := json.Marshal(map[string]string{"error": msg})
	return events.APIGatewayProxyResponse{
		StatusCode: code,
		Headers:    map[string]string{"Content-Type": "application/json"},
		Body:       string(body),
	}
}

func strPtr(s string) *string {
	return &s
}

func main() {
	lambda.Start(handler)
}
