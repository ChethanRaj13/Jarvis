using windowsAssistant.UI.Models;

namespace windowsAssistant.UI.Agents;

public interface ICoordinatorAgent
{
    void ReceiveTask(AgentTask task);

    void DispatchTask(AgentTask task);

    void AssignExecutor(AgentTask task);

    void VerifyTask(AgentTask task);

    void CompleteTask(AgentTask task);
}
