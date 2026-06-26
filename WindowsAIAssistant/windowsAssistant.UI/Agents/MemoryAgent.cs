using windowsAssistant.UI.Models;

namespace windowsAssistant.UI.Agents;

public class MemoryAgent : IMemoryAgent
{
    public void SaveTaskHistory(AgentTask task)
    {
        // TODO: Save task history to memory storage.
    }

    public IEnumerable<AgentTask> LoadTaskHistory()
    {
        // TODO: Load task history from memory storage.
        return Enumerable.Empty<AgentTask>();
    }
}
