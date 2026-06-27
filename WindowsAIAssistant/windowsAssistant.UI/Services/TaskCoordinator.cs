using System.Threading.Tasks;
using windowsAssistant.UI.Contracts;
using windowsAssistant.UI.Models;

namespace windowsAssistant.UI.Services;

public class TaskCoordinator : ITaskCoordinator
{
    private readonly ITaskQueue _queue;
    private readonly ILifecycleManager _lifecycle;
    private readonly IRuntimeStateStore _state;

    public TaskCoordinator(ITaskQueue queue, ILifecycleManager lifecycle, IRuntimeStateStore state)
    {
        _queue = queue;
        _lifecycle = lifecycle;
        _state = state;
    }

    public async Task SendPlanAsync(TaskExecutionPlan plan, TaskContext? context = null)
    {
        // create a TaskItem and persist
        var item = new TaskItem
        {
            Title = "Generated Task",
            Description = "Plan received from planner",
            Plan = plan,
            Context = context
        };

        await _lifecycle.CreateAsync(item);
        await _queue.EnqueueAsync(item);
        await _state.SaveStateAsync(item);
    }
}
