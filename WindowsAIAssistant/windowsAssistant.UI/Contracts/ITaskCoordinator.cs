using System.Threading.Tasks;
using windowsAssistant.UI.Models;

namespace windowsAssistant.UI.Contracts;

public interface ITaskCoordinator
{
    Task SendPlanAsync(TaskExecutionPlan plan, TaskContext? context = null);
}
