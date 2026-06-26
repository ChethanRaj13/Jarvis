using System.Collections.ObjectModel;
using CommunityToolkit.Mvvm.ComponentModel;
using windowsAssistant.UI.Models;

namespace windowsAssistant.UI.ViewModels;

public partial class ChatViewModel : ObservableObject
{
    public ObservableCollection<ChatMessage> Messages { get; } = new();
}
