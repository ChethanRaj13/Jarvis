using windowsAssistant.UI.Models;

namespace windowsAssistant.UI.Agents;

public interface IExecutorAgent
{
    void ExecuteTask(AgentTask task);
}
