# Subtitle Format Lab contract

`/subtitle/formats` là công cụ Web-native, stateless để chuẩn hóa văn bản caption. Nó được tách khỏi Bot, Core Bridge, Subtitle Studio project database và mọi pipeline media.

## Chức năng hiện có

- `POST /api/v1/subtitle-studio/format-tools/convert`
- `srt_to_vtt`: parse SRT hợp lệ rồi render lại VTT chuẩn hóa.
- `vtt_to_srt`: parse VTT hợp lệ rồi render lại SRT chuẩn hóa.
- `text_to_srt`: chia văn bản thành tối đa 12 từ/cue, dùng timing mili-giây xác định và giới hạn 500 cues.

Endpoint yêu cầu signed session và CSRF. Request chỉ nhận `mode`, `content` và `duration_seconds`; `extra="forbid"` chặn file, URL, account ID, provider/job handle và mọi trường không thuộc contract.

## Biên giới authority

- Không import hoặc sửa `bot.py`; thuật toán 12 từ/cue chỉ tham khảo tĩnh từ baseline Bot.
- Không gọi Bot, Core Bridge, provider, PayOS, wallet, Telegram, webhook hoặc subprocess.
- Không lưu content vào project, asset, job, audit detail hoặc browser persistent storage.
- Không upload/chọn file, không tạo output media, file, download URL hay delivery.
- VTT header metadata, cue identifier, `NOTE`, `STYLE` và `REGION` không được giữ hoặc diễn giải như cấu hình.

Phản hồi thành công có `status=completed` chỉ để xác nhận text transform đã xong. Nó luôn kèm:

```json
{
  "execution": "web_native_text_transform",
  "text_transform_completed": true,
  "provider_called": false,
  "asr_called": false,
  "translation_called": false,
  "tts_called": false,
  "dubbing_called": false,
  "media_uploads": false,
  "output_created": false,
  "output_delivery": "none",
  "job_created": false,
  "payment_charged": false
}
```

`completed` ở đây không phải job completed và không chứng minh ASR, dịch, TTS, dubbing hay media delivery.

## Giới hạn và fail-closed

- Body route family tối đa 128 KiB trước khi JSON được parse.
- Nội dung tối đa 120.000 ký tự / 96 KiB UTF-8; kết quả text tối đa 96 KiB.
- Tối đa 500 cues, duration từ `0` đến `86.400` giây và cue luôn nằm trong một ngày.
- Timing hoặc caption không hợp lệ trả `422`; output quá lớn trả envelope `guarded` với `WEB_SUBTITLE_FORMAT_OUTPUT_TOO_LARGE` và không trả text.
- Portal chỉ render response sau khi kiểm tra toàn bộ boundary trên; data sai hoặc từ session cũ bị bỏ qua.

## Không phải phạm vi của module

Audio/video upload, ASR, dịch phụ đề, dubbing, TTS, mux, file export, asset delivery, Xu, PayOS, provider và job canonical vẫn cần contract riêng. Chúng không được suy diễn từ Format Lab.
