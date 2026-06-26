namespace windowsAssistant.UI.Services;

public class SpeechToTextService : ISpeechToTextService
{
    public Task<string> TranscribeAsync(CancellationToken cancellationToken = default)
    {
        // TODO: Add speech-to-text integration.
        return Task.FromResult(string.Empty);
    }
}
