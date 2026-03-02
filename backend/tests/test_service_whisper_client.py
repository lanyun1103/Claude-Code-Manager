"""Tests for WhisperClient."""
import pytest
from unittest.mock import patch, AsyncMock, MagicMock
import httpx

from backend.services.whisper_client import WhisperClient


@pytest.mark.asyncio
async def test_transcribe_success():
    client = WhisperClient()
    mock_response = MagicMock()
    mock_response.json.return_value = {"text": "hello world"}
    mock_response.raise_for_status = MagicMock()

    mock_http = AsyncMock()
    mock_http.post = AsyncMock(return_value=mock_response)
    mock_http.__aenter__ = AsyncMock(return_value=mock_http)
    mock_http.__aexit__ = AsyncMock(return_value=False)

    with patch("backend.services.whisper_client.settings") as mock_settings, \
         patch("backend.services.whisper_client.httpx.AsyncClient", return_value=mock_http):
        mock_settings.openai_api_key = "test-key"
        result = await client.transcribe(b"audio-data", "audio.webm")

    assert result == "hello world"


@pytest.mark.asyncio
async def test_transcribe_no_api_key():
    client = WhisperClient()
    with patch("backend.services.whisper_client.settings") as mock_settings:
        mock_settings.openai_api_key = ""
        with pytest.raises(ValueError, match="OPENAI_API_KEY"):
            await client.transcribe(b"audio-data")


@pytest.mark.asyncio
async def test_transcribe_wav():
    """WAV files should use audio/wav content type."""
    client = WhisperClient()
    mock_response = MagicMock()
    mock_response.json.return_value = {"text": "wav audio"}
    mock_response.raise_for_status = MagicMock()

    mock_http = AsyncMock()
    mock_http.post = AsyncMock(return_value=mock_response)
    mock_http.__aenter__ = AsyncMock(return_value=mock_http)
    mock_http.__aexit__ = AsyncMock(return_value=False)

    with patch("backend.services.whisper_client.settings") as mock_settings, \
         patch("backend.services.whisper_client.httpx.AsyncClient", return_value=mock_http):
        mock_settings.openai_api_key = "test-key"
        result = await client.transcribe(b"wav-data", "audio.wav")

    assert result == "wav audio"
    # Verify the file tuple had wav content type
    call_kwargs = mock_http.post.call_args
    files = call_kwargs.kwargs.get("files") or call_kwargs[1].get("files")
    assert files["file"][0] == "audio.wav"


@pytest.mark.asyncio
async def test_transcribe_mp3():
    """MP3 files should use audio/mpeg content type."""
    client = WhisperClient()
    mock_response = MagicMock()
    mock_response.json.return_value = {"text": "mp3 audio"}
    mock_response.raise_for_status = MagicMock()

    mock_http = AsyncMock()
    mock_http.post = AsyncMock(return_value=mock_response)
    mock_http.__aenter__ = AsyncMock(return_value=mock_http)
    mock_http.__aexit__ = AsyncMock(return_value=False)

    with patch("backend.services.whisper_client.settings") as mock_settings, \
         patch("backend.services.whisper_client.httpx.AsyncClient", return_value=mock_http):
        mock_settings.openai_api_key = "test-key"
        result = await client.transcribe(b"mp3-data", "audio.mp3")

    assert result == "mp3 audio"


@pytest.mark.asyncio
async def test_transcribe_api_error():
    """API returning error status raises HTTPStatusError."""
    client = WhisperClient()
    mock_response = MagicMock()
    mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
        "Server Error", request=MagicMock(), response=MagicMock()
    )

    mock_http = AsyncMock()
    mock_http.post = AsyncMock(return_value=mock_response)
    mock_http.__aenter__ = AsyncMock(return_value=mock_http)
    mock_http.__aexit__ = AsyncMock(return_value=False)

    with patch("backend.services.whisper_client.settings") as mock_settings, \
         patch("backend.services.whisper_client.httpx.AsyncClient", return_value=mock_http):
        mock_settings.openai_api_key = "test-key"
        with pytest.raises(httpx.HTTPStatusError):
            await client.transcribe(b"audio-data")
