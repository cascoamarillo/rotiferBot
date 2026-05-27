# Rotifer Literature Bot for Bluesky

A bot that searches PubMed for recent rotifer research papers and posts them to Bluesky automatically.

## Features

- 🔍 Daily searches for rotifer papers on PubMed
- 📝 Smart post formatting with biological context
- 🚫 Duplicate detection to avoid reposting
- 🤖 Fully automated via GitHub Actions
- 🦠 Covers rotifers, bdelloids, and related terms

## Setup Instructions

### 1. Fork/Clone this repository

### 2. Create a Bluesky App Password
1. Go to [Bluesky Settings](https://bsky.app/settings)
2. Navigate to "Privacy and security" > "App passwords"
3. Create a new app password (save this, you can't see it again!)

### 3. Set GitHub Secrets
In your GitHub repository:
1. Go to Settings > Secrets and variables > Actions
2. Add two secrets:
   - `BLUESKY_HANDLE`: Your Bluesky handle (e.g., `yourname.bsky.social`)
   - `BLUESKY_PASSWORD`: The app password you created

### 4. Enable GitHub Actions
1. Go to the Actions tab in your repository
2. Click "I understand my workflows and want to enable them"

### 5. Test the Bot
- Go to Actions > "Rotifer Literature Bot"
- Click "Run workflow" to test manually
- Check that it posts successfully to your Bluesky account

## How it Works

1. **Search**: Queries PubMed for papers containing "rotifer", "rotifers", or "bdelloid" from the last 30 days
2. **Filter**: Checks against a local database to avoid reposting
3. **Format**: Creates engaging posts with:
   - Contextual hooks (🧬 for bdelloids, 💤 for cryptobiosis, etc.)
   - Paper title, first author, journal
   - Direct link to PubMed
4. **Post**: Shares up to 1 paper per run to respect the small research community

## Schedule

- Runs daily at 9 AM UTC
- Can be triggered manually from GitHub Actions  
- **Community-friendly**: Maximum 1 post per day to respect the small rotifer research community
- Searches papers from last 30 days to catch everything without being too frequent

## Example Posts

```
#Rotifersky

Evolutionary genomics reveals unique DNA repair mechanisms in bdelloid rotifers • Rodriguez et al. • Nature (2024)

https://doi.org/10.1038/s41586-024-12345-6
```

```
#Rotifersky

Molecular basis of anhydrobiosis in tardigrades and rotifers • Chen et al. • Cell (2024)

https://doi.org/10.1016/j.cell.2024.01.234
```

## Customization

### Modify Search Terms
Edit the `search_terms` variable in `rotifer_bot.py`:
```python
search_terms = "(rotifer[Title/Abstract] OR rotifers[Title/Abstract] OR bdelloid[Title/Abstract])"
```

### Adjust Posting Schedule
Modify the cron expression in `.github/workflows/rotifer-bot.yml`:
```yaml
schedule:
  - cron: '0 9 * * *'  # Daily at 9 AM UTC
  - cron: '0 21 * * *' # Add evening posts
```

### Change Post Format
Modify the `format_paper_post()` function to customize how papers are presented.

## Files

- `rotifer_bot.py`: Main bot script
- `.github/workflows/rotifer-bot.yml`: GitHub Actions workflow
- `posted_papers.json`: Tracks posted papers (auto-generated)

## Troubleshooting

### Bot not posting?
- Check GitHub Actions logs in the Actions tab
- Verify your Bluesky credentials in repository secrets
- Make sure your app password is valid

### No papers found?
- The bot only looks for papers from the last 7 days
- Try running manually to see search results
- Rotifer research isn't published daily - this is normal!

### Want to test locally?
```bash
export BLUESKY_HANDLE="your.handle.bsky.social"
export BLUESKY_PASSWORD="your-app-password"
python rotifer_bot.py
```

## Contributing

Feel free to:
- Add more search terms for rotifer research
- Improve the post formatting
- Add support for bioRxiv preprints
- Enhance the biological context detection

## License

MIT License - feel free to adapt for other research topics!
