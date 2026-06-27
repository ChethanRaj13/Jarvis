using System.Collections.Concurrent;
using System.Threading.Tasks;
using windowsAssistant.UI.Contracts;
using windowsAssistant.UI.Models;

namespace windowsAssistant.UI.Services;

public class TaskQueue : ITaskQueue
{
    private readonly ConcurrentQueue<TaskItem> _queue = new();

    public Task EnqueueAsync(TaskItem item)
    {
        _queue.Enqueue(item);
        return Task.CompletedTask;
    }

    public Task<TaskItem?> DequeueAsync()
    {
        if (_queue.TryDequeue(out var item)) return Task.FromResult<TaskItem?>(item);
        return Task.FromResult<TaskItem?>(null);
    }

    public Task<TaskItem?> PeekAsync()
    {
        if (_queue.TryPeek(out var item)) return Task.FromResult<TaskItem?>(item);
        return Task.FromResult<TaskItem?>(null);
    }
}
