using System.Collections.Generic;
using System.Linq;
using System.Text.Json.Serialization;
using System.Threading.Tasks;
using windowsAssistant.UI.Models;

namespace windowsAssistant.UI.Services;

public class PlanningService
{
    private readonly ApiClient _apiClient = new();

    public async Task<List<PlanStep>> GeneratePlanAsync(string command)
    {
        if (string.IsNullOrWhiteSpace(command))
        {
            return new List<PlanStep>();
        }

        var response = await _apiClient.PostJsonAsync<PlanApiResponse>("/plan", new { text = command });
        return FlattenPlan(response);
    }

    private static List<PlanStep> FlattenPlan(PlanApiResponse response)
    {
        var steps = new List<PlanStep>();
        if (response?.Plan?.SubGoalPlans == null)
        {
            return steps;
        }

        foreach (var subGoal in response.Plan.SubGoalPlans)
        {
            if (!string.IsNullOrWhiteSpace(subGoal.SubGoalDescription))
            {
                steps.Add(new PlanStep
                {
                    StepNumber = 0,
                    Action = $"Sub-goal: {subGoal.SubGoalDescription}",
                    ToolOrMethod = null
                });
            }

            foreach (var step in subGoal.Steps)
            {
                steps.Add(new PlanStep
                {
                    StepNumber = step.StepNumber,
                    Action = step.Action,
                    ToolOrMethod = step.ToolOrMethod
                });
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
