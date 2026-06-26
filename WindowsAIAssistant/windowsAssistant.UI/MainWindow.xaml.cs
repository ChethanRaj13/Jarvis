using System;
using System.Collections.Generic;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Media;
using windowsAssistant.UI.Models;
using windowsAssistant.UI.Services;

namespace windowsAssistant.UI;

public partial class MainWindow : Window
{
    private readonly PlanningService planningService = new();
    private readonly ExecutionService executionService = new();
    private readonly VerificationService verificationService = new();

    private readonly List<ChatMessage> chatHistory = new();
    private List<string> currentPlan = new();

    public MainWindow()
    {
        InitializeComponent();
    }

    private async void SendButton_Click(object sender, RoutedEventArgs e)
    {
        string userMessage = CommandInput.Text;

        if (string.IsNullOrWhiteSpace(userMessage))
            return;

        // Store user message
        chatHistory.Add(new ChatMessage
        {
            Sender = "User",
            Content = userMessage
        });

        // Show user message
        TextBlock messageBlock = new TextBlock
        {
            Text = "User: " + userMessage,
            Foreground = Brushes.White,
            FontSize = 16,
            Margin = new Thickness(0, 10, 0, 10),
            TextWrapping = TextWrapping.Wrap
        };

        ChatPanel.Children.Add(messageBlock);
        CommandInput.Clear();

        // Disable input while we wait on the API so the user can't double-fire requests.
        SendButton.IsEnabled = false;
        CommandInput.IsEnabled = false;

        // Generate plan from the backend API
        currentPlan = await planningService.GeneratePlanAsync(userMessage);

        // Store assistant response
        string assistantReply = string.Join("\n", currentPlan);

        chatHistory.Add(new ChatMessage
        {
            Sender = "Assistant",
            Content = assistantReply
        });

        // Show assistant heading
        TextBlock assistantHeader = new TextBlock
        {
            Text = "Assistant: Execution Plan",
            Foreground = Brushes.LightBlue,
            FontSize = 16,
            FontWeight = FontWeights.Bold,
            Margin = new Thickness(0, 10, 0, 10)
        };

        ChatPanel.Children.Add(assistantHeader);

        // Show plan
        foreach (var step in currentPlan)
        {
            TextBlock stepBlock = new TextBlock
            {
                Text = "• " + step,
                Foreground = Brushes.LightBlue,
                FontSize = 14,
                Margin = new Thickness(20, 2, 0, 2),
                TextWrapping = TextWrapping.Wrap
            };

            ChatPanel.Children.Add(stepBlock);
        }

        try
        {
            TaskNameText.Text = userMessage;
            TaskStatusText.Text = "Planning";

            ProgressPanel.Visibility = Visibility.Visible;

            TaskProgressBar.Value = 25;
            ProgressText.Text = "25%";

            ApproveButton.Visibility = Visibility.Visible;
        }
        catch (Exception ex)
        {
            TextBlock errorBlock = new TextBlock
            {
                Text = "Assistant: " + ex.Message,
                Foreground = Brushes.OrangeRed,
                FontSize = 14,
                Margin = new Thickness(0, 10, 0, 10),
                TextWrapping = TextWrapping.Wrap
            };
            ChatPanel.Children.Add(errorBlock);
        }
        finally
        {
            SendButton.IsEnabled = true;
            CommandInput.IsEnabled = true;
        }
    }

    private async void ApproveButton_Click(object sender, RoutedEventArgs e)
    {
        TaskStatusText.Text = "Executing";

        TaskProgressBar.Value = 50;
        ProgressText.Text = "50%";

        var logs = await executionService.ExecuteAsync(currentPlan);

        foreach (var log in logs)
        {
            TextBlock logBlock = new TextBlock
            {
                Text = "Assistant: " + log,
                Foreground = Brushes.LightGreen,
                FontSize = 16,
                Margin = new Thickness(0, 8, 0, 8),
                TextWrapping = TextWrapping.Wrap
            };

            ChatPanel.Children.Add(logBlock);
        }

        var verificationSummary = await verificationService.VerifyAsync(currentPlan, TaskNameText.Text);
        TextBlock verificationBlock = new TextBlock
        {
            Text = "Assistant: Verification -> " + verificationSummary,
            Foreground = Brushes.LightSkyBlue,
            FontSize = 14,
            Margin = new Thickness(0, 8, 0, 8),
            TextWrapping = TextWrapping.Wrap
        };

        ChatPanel.Children.Add(verificationBlock);

        TaskProgressBar.Value = 100;
        ProgressText.Text = "100%";

        TaskStatusText.Text = "Completed";

        ApproveButton.Visibility = Visibility.Collapsed;
    }
}