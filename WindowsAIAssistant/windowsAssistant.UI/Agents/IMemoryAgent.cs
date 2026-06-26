using windowsAssistant.UI.Models;

namespace windowsAssistant.UI.Agents;

public interface IMemoryAgent
{
    void SaveTaskHistory(AgentTask task);

    IEnumerable<AgentTask> LoadTaskHistory();
}
