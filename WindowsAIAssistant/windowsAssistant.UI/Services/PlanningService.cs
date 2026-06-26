using System.Collections.Generic;
using System.Text.Json.Serialization;
using System.Threading.Tasks;

namespace windowsAssistant.UI.Services;

public class PlanningService
{
    private readonly ApiClient _apiClient = new();

    public async Task<List<string>> GeneratePlanAsync(string command)
    {
        if (string.IsNullOrWhiteSpace(command))
        {
            return new List<string>();
        }

        var response = await _apiClient.PostJsonAsync<PlanApiResponse>("/plan", new { text = command });
        return FlattenPlan(response);
    }

    private static List<string> FlattenPlan(PlanApiResponse response)
    {
        var steps = new List<string>();
        if (response?.Plan?.SubGoalPlans == null)
        {
            return steps;
        }

        foreach (var subGoal in response.Plan.SubGoalPlans)
        {
            steps.Add($"[{subGoal.SubGoalId}] {subGoal.SubGoalDescription}");
            foreach (var step in subGoal.Steps)
            {
                string toolSuffix = string.IsNullOrWhiteSpace(step.ToolOrMethod)
                    ? ""
                    : $" [{step.ToolOrMethod}]";

                steps.Add($"{step.StepNumber}. {step.Action}{toolSuffix}");
            }
        }

        return steps;
    }
}

public class PlanApiResponse
{
    [JsonPropertyName("intent")]
    public StructuredIntent? Intent { get; set; }

    [JsonPropertyName("plan")]
    public TaskPlan? Plan { get; set; }
}
