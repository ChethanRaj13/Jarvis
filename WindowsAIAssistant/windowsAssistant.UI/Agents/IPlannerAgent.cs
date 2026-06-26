using windowsAssistant.UI.Models;

namespace windowsAssistant.UI.Agents;

public interface IPlannerAgent
{
    void PlanTask(AgentTask task);
}
