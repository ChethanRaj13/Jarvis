namespace windowsAssistant.UI.Services;

public interface ISpeechToTextService
{
    Task<string> TranscribeAsync(CancellationToken cancellationToken = default);
}
