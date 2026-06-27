using System.Threading.Tasks;
using windowsAssistant.UI.Contracts;
using windowsAssistant.UI.Models;

namespace windowsAssistant.UI.Services;

public class LifecycleManager : ILifecycleManager
{
    private readonly IRuntimeStateStore _stateStore;

    public LifecycleManager(IRuntimeStateStore stateStore)
    {
        _stateStore = stateStore;
    }

    public async Task<TaskItem> CreateAsync(TaskItem item)
    {
        item.Status = windowsAssistant.UI.Models.TaskStatus.Created;
        await _stateStore.SaveStateAsync(item);
        return item;
    }

    public Task<TaskItem?> GetAsync(string taskId)
        => _stateStore.LoadStateAsync(taskId);

    public async Task UpdateStatusAsync(string taskId, windowsAssistant.UI.Models.TaskStatus status)
    {
        var item = await _stateStore.LoadStateAsync(taskId);
        if (item == null) return;
        item.Status = status;
        await _stateStore.SaveStateAsync(item);
    }
}
