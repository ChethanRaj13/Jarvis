namespace windowsAssistant.UI.Models;

public class ChatMessage
{
    public string Sender { get; set; } = "";
    public string Content { get; set; } = "";
    public DateTime Timestamp { get; set; } = DateTime.Now;
}