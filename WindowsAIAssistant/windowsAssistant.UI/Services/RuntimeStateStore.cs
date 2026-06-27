using System.Collections.Concurrent;
using System.Threading.Tasks;
using windowsAssistant.UI.Contracts;
using windowsAssistant.UI.Models;

namespace windowsAssistant.UI.Services;

public class RuntimeStateStore : IRuntimeStateStore
{
    private readonly ConcurrentDictionary<string, TaskItem> _store = new();

    public Task SaveStateAsync(TaskItem item)
    {
        _store[item.TaskId] = item;
        return Task.CompletedTask;
    }

    public Task<TaskItem?> LoadStateAsync(string taskId)
    {
        _store.TryGetValue(taskId, out var item);
        return Task.FromResult<TaskItem?>(item);
    }
}
