namespace windowsAssistant.UI.Services;

public class TextToSpeechService : ITextToSpeechService
{
    public Task SpeakAsync(string text, CancellationToken cancellationToken = default)
    {
        // TODO: Add text-to-speech integration.
        return Task.CompletedTask;
    }
}
