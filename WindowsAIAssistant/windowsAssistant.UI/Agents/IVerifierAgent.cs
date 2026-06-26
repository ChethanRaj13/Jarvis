using windowsAssistant.UI.Models;

namespace windowsAssistant.UI.Agents;

public interface IVerifierAgent
{
    void VerifyTask(AgentTask task);
}
