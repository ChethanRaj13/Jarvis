using System;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Media;
using windowsAssistant.UI.Services;

namespace windowsAssistant.UI;

public partial class MainWindow : Window
{
    // PlanningService kept here in case you still use it elsewhere (e.g. to
    // turn a StructuredIntent into executable steps). Remove if unused.
    private PlanningService planningService = new PlanningService();
    private readonly IntentApiClient intentApiClient = new IntentApiClient("http://localhost:8000");

    public MainWindow()
    {
        InitializeComponent();
    }

    private async void SendButton_Click(object sender, RoutedEventArgs e)
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
        CommandInput.Clear();

        // Disable input while we wait on the API so the user can't double-fire requests.
        SendButton.IsEnabled = false;
        CommandInput.IsEnabled = false;

        try
        {
            StructuredIntent intent = await intentApiClient.ParseAsync(userMessage);

            TextBlock assistantHeader = new TextBlock
            {
                Text = $"Assistant: Intent = {intent.IntentType} (confidence {intent.Confidence:P0})",
                Foreground = Brushes.LightBlue,
                FontSize = 16,
                FontWeight = FontWeights.Bold,
                Margin = new Thickness(0, 10, 0, 10),
                TextWrapping = TextWrapping.Wrap
            };
            ChatPanel.Children.Add(assistantHeader);

            if (intent.Entities.Count > 0)
            {
                foreach (var entity in intent.Entities)
                {
                    TextBlock entityBlock = new TextBlock
                    {
                        Text = $"• {entity.Type}: {entity.Value}",
                        Foreground = Brushes.LightBlue,
                        FontSize = 14,
                        Margin = new Thickness(20, 2, 0, 2),
                        TextWrapping = TextWrapping.Wrap
                    };
                    ChatPanel.Children.Add(entityBlock);
                }
            }

            TextBlock riskBlock = new TextBlock
            {
                Text = $"Risk: {intent.RiskLevel}" +
                       (intent.RiskReasons.Count > 0 ? $" — {string.Join("; ", intent.RiskReasons)}" : ""),
                Foreground = intent.RiskLevel == "high" ? Brushes.OrangeRed : Brushes.LightGray,
                FontSize = 13,
                Margin = new Thickness(20, 2, 0, 10),
                TextWrapping = TextWrapping.Wrap
            };
            ChatPanel.Children.Add(riskBlock);

            // Now feed the structured intent into your existing planning flow.
            // Adjust this call to match whatever PlanningService expects once
            // it's updated to accept a StructuredIntent instead of raw text.
            var plan = planningService.GeneratePlan(userMessage);

            TextBlock planHeader = new TextBlock
            {
                Text = "Assistant: Execution Plan",
                Foreground = Brushes.LightBlue,
                FontSize = 16,
                FontWeight = FontWeights.Bold,
                Margin = new Thickness(0, 10, 0, 10)
            };
            ChatPanel.Children.Add(planHeader);

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
        }
        catch (IntentApiException ex)
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