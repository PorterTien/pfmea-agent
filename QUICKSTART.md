# Quick Start Guide

## 🚀 One-Command Setup

Just run:

```bash
./start.sh
```

**To start fresh (clear all previous analyses):**

```bash
./start.sh --clear-db
```

That's it! The script will:
- Check all prerequisites
- Install dependencies
- Configure everything
- Clear database (if `--clear-db` flag is used)
- Start both servers

Then open your browser to: **http://localhost:5173**

## What You Need

Before running `./start.sh`, make sure you have:

1. **Python 3.11+** - Check with: `python3 --version`
2. **Node.js 18+** - Check with: `node --version`
3. **Ollama** - Install from https://ollama.ai

The script will check these and guide you if anything is missing.

## Stopping the Servers

Press `Ctrl+C` in the terminal where you ran `./start.sh`

## Troubleshooting

### "Command not found: ollama"
Install Ollama from https://ollama.ai

### "Port already in use"
Stop any processes using ports 8000 or 5173, or modify the ports in the config files.

### "Model not found"
The script will try to pull `gpt-oss:120b` automatically. If it fails, run:
```bash
ollama pull gpt-oss:120b
```

## Need Help?

Check the full [README.md](README.md) for detailed documentation.

