namespace windowsAssistant.UI.Services;

public interface ITextToSpeechService
{
    Task SpeakAsync(string text, CancellationToken cancellationToken = default);
}
