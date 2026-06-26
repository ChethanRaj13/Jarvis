using System.Collections.ObjectModel;
using CommunityToolkit.Mvvm.ComponentModel;
using CommunityToolkit.Mvvm.Input;
using windowsAssistant.UI.Models;
using windowsAssistant.UI.Services;

namespace windowsAssistant.UI.ViewModels;

public partial class TaskManagerViewModel : ObservableObject
{
    private readonly ITaskManagerService taskManagerService;

    [ObservableProperty]
    private AgentTask? selectedTask;

    public TaskManagerViewModel(ITaskManagerService taskManagerService)
    {
        this.taskManagerService = taskManagerService;
        Tasks = taskManagerService.GetAllTasks();
    }

    public ObservableCollection<AgentTask> Tasks { get; }

    [RelayCommand]
    private void AddTask()
    {
        // TODO: Create a task from UI input when the Task Manager UI exposes it.
    }

    [RelayCommand(CanExecute = nameof(HasSelectedTask))]
    private void CancelTask()
    {
        // TODO: Cancel selected task through orchestration flow.
    }

    [RelayCommand(CanExecute = nameof(HasSelectedTask))]
    private void PauseTask()
    {
        // TODO: Pause selected task through orchestration flow.
    }

    [RelayCommand(CanExecute = nameof(HasSelectedTask))]
    private void ResumeTask()
    {
        // TODO: Resume selected task through orchestration flow.
    }

    [RelayCommand(CanExecute = nameof(HasSelectedTask))]
    private void RetryTask()
    {
        // TODO: Retry selected task through orchestration flow.
    }

    [RelayCommand]
    private void ClearCompleted()
    {
        // TODO: Clear completed tasks after persistence behavior is defined.
    }

    [RelayCommand]
    private void Refresh()
    {
        // TODO: Refresh tasks from persistence/service layer.
    }

    private bool HasSelectedTask()
    {
        return SelectedTask is not null;
    }

    partial void OnSelectedTaskChanged(AgentTask? value)
    {
        CancelTaskCommand.NotifyCanExecuteChanged();
        PauseTaskCommand.NotifyCanExecuteChanged();
        ResumeTaskCommand.NotifyCanExecuteChanged();
        RetryTaskCommand.NotifyCanExecuteChanged();
    }
}
