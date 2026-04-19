# rythu-mitra

WhatsApp-based AI agricultural assistant for small farmers in Nizamabad district, Telangana.

## Folders

- `data/`: district reference data, price history, and schemes
- `engine/`: crop logic, prices, weather, district caps, and season planning
- `bot/`: WhatsApp routing, farmer profile flow, voice integration, and alerts
- `disease/`: training, model loading, and inference helpers
- `dashboard/`: React UI for district map, mandi prices, and bot demo
- `docs/`: architecture and scenario artifacts
- `scripts/`: one-off seed and test scripts

## Week 3 status

- FastAPI webhook: `/whatsapp`
- Progressive farmer profile flow: `bot/farmer_profile.py`
- Telugu STT/TTS: `bot/telugu_voice.py`
- Voice-capable WhatsApp handler: `bot/whatsapp_handler.py`
- Railway launch config: `Procfile` + `runtime.txt`

## Local checks

Run the voice smoke test:

```bash
python3 scripts/test_whatsapp_voice.py
```

Run the text engine smoke test:

```bash
python3 scripts/test_engine.py
```

## Dependencies

- `requirements.txt` is the slim Railway/runtime set for the live WhatsApp service.
- `requirements-ml.txt` adds the heavy disease-model stack for local training or Colab work.
- This split keeps Railway free-tier builds below the 4 GB image cap.

## Railway deploy

1. Push this repo to GitHub.
2. Create a new Railway project from the GitHub repo.
3. Add all `.env` variables from `.env.example`.
4. Set `PUBLIC_BASE_URL` to the Railway app URL after first deploy.
5. In Twilio WhatsApp sandbox, set the webhook to:
   `/whatsapp`
6. Verify `/health` returns `{"status":"ok","service":"rythu-mitra"}`.

## Notes

- `.env` is local-only and should never be committed with real secrets.
- `TWILIO_WHATSAPP_NUMBER` should be the sandbox number without the `whatsapp:` prefix.
- Sarvam TTS uses `manan` under the hood; the code accepts the brief's `maan` name and maps it safely.
