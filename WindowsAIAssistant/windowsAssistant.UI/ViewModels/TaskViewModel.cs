using CommunityToolkit.Mvvm.ComponentModel;
using windowsAssistant.UI.Models;

namespace windowsAssistant.UI.ViewModels;

public partial class TaskViewModel : ObservableObject
{
    [ObservableProperty]
    private AgentTask? task;
}
