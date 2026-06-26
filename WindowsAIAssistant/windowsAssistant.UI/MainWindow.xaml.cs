using System.Windows;
using System.Windows.Controls;
using System.Windows.Media;
using windowsAssistant.UI.Services;

namespace windowsAssistant.UI;

public partial class MainWindow : Window
{
    private PlanningService planningService = new PlanningService();

    public MainWindow()
    {
        InitializeComponent();
    }

    private void SendButton_Click(object sender, RoutedEventArgs e)
    {
        string userMessage = CommandInput.Text;

        if (string.IsNullOrWhiteSpace(userMessage))
            return;

        TextBlock messageBlock = new TextBlock
        {
            Text = "User: " + userMessage,
            Foreground = Brushes.White,
            FontSize = 16,
            Margin = new Thickness(0, 10, 0, 10),
            TextWrapping = TextWrapping.Wrap
        };

        ChatPanel.Children.Add(messageBlock);

        var plan = planningService.GeneratePlan(userMessage);

        TextBlock assistantHeader = new TextBlock
        {
            Text = "Assistant: Execution Plan",
            Foreground = Brushes.LightBlue,
            FontSize = 16,
            FontWeight = FontWeights.Bold,
            Margin = new Thickness(0, 10, 0, 10)
        };

        ChatPanel.Children.Add(assistantHeader);

        foreach (var step in plan)
        {
            TextBlock stepBlock = new TextBlock
            {
                Text = "• " + step,
                Foreground = Brushes.LightBlue,
                FontSize = 14,
                Margin = new Thickness(20, 2, 0, 2)
            };

            ChatPanel.Children.Add(stepBlock);
        }

        TaskNameText.Text = userMessage;
        TaskStatusText.Text = "Planning";

        ProgressPanel.Visibility = Visibility.Visible;

        TaskProgressBar.Value = 25;
        ProgressText.Text = "25%";

        ApproveButton.Visibility = Visibility.Visible;

        CommandInput.Clear();
    }

    private void ApproveButton_Click(object sender, RoutedEventArgs e)
    {
        TaskStatusText.Text = "Executing";

        TaskProgressBar.Value = 50;
        ProgressText.Text = "50%";

        TextBlock executionMessage = new TextBlock
        {
            Text = "Assistant: Execution Started...",
            Foreground = Brushes.LightGreen,
            FontSize = 16,
            Margin = new Thickness(0, 10, 0, 10)
        };

        ChatPanel.Children.Add(executionMessage);

        ApproveButton.Visibility = Visibility.Collapsed;
    }
}