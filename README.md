# URLScan Public Xtream Scraper

[![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)](https://python.org)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](https://raw.githubusercontent.com/kidpoleon/urlscan-public-xtream-scrape/refs/heads/main/LICENSE)
[![Status](https://img.shields.io/badge/Status-Active-brightgreen.svg)]()

> **A fast, async‑enabled scraper that finds publicly viewable XTream IPTV panel credentials from urlscan.io, validates them in parallel, and exports clean, ready‑to‑use results.**

---

## 🚀 Features

- **Multiple search presets** for XTream panels (`/live/play/`, `/get.php`, `streaming/clients_live.php`, etc.).
- **Date‑window filtering** (1–365 days) to focus on recent, likely‑live scans.
- **Async validation** with `aiohttp` + Rich progress bars for fast, non‑blocking credential checks.
- **Smart filtering** to drop obvious junk (parking pages, assets, JS/CSS files).
- **Automatic deduplication** and per‑run timestamped output directories.
- **JSON‑only exports** (valid + all) with expiration and status metadata.
- **Graceful Ctrl+C handling** and clean error reporting.

---

## 📦 Installation

1. **Clone the repo**

   ```bash
   git clone https://github.com/kidpoleon/urlscan-public-xtream-scrape.git
   cd urlscan-public-xtream-scrape
   ```

2. **Install dependencies**

   ```bash
   pip install -r requirements.txt
   ```

3. **Run the scraper**

   ```bash
   python main.py
   ```

---

## 🔑 How to Acquire a urlscan.io API Key

1. **Sign up** at [urlscan.io](https://urlscan.io/sign-up).
2. After logging in, go to **Account → API**.
3. Copy your **API key** (starts with `019a...`).

> **Tip:** Free accounts have generous daily limits; keep `max_scans` reasonable (≤500) to avoid hitting caps.

---

## 🧭 Which Query Option to Choose

When you run the script, you’ll see a numbered menu. Pick the one that matches the panels you’re targeting:

| Option | Query | Typical Use |
|--------|-------|-------------|
| **1** | `page.url:"/live/play/"` | Panels that expose a `/live/play/` path. |
| **2** | `page.url:"/get.php?username="` | Classic XTream `get.php` endpoints with query‑style credentials. |
| **3** | `page.url:"/player_api.php?username="` | Direct `player_api.php` references. |
| **4** | `page.url:"&type=m3u_plus"` | M3U playlist type hints. |
| **5** | `page.url:"&type=m3u"` | Generic M3U type. |
| **6** | `page.url:"&type=m3u8"` | HLS/M3U8 type. |
| **7** | `page.url:"&output=hls"` | HLS output references. |
| **8** | `page.url:"&output=ts"` | Transport‑stream output. |
| **9** | `page.url:"streaming/clients_live.php?username="` | Alternate panel endpoint pattern. |
| **0** | **ALL OF THE ABOVE (OR‑combined)** | Broad search across all patterns (may hit urlscan limits early). |

**Recommendations**

- For **high‑quality results**, start with **2** or **9**.
- For **broad coverage**, try **0**, but be aware that urlscan may stop paginating early for very long OR queries.
- Combine multiple runs with different presets to maximize coverage.

---

## 📁 Where to Look for Output Files

Every run creates a **timestamped folder** under `output/`:

```
output/
└─ 1970-01-01_00-00-00/
   ├─ xtream_valid.json   # ✅ Valid, non‑expired credentials
   └─ xtream_all.json     # 📦 All scraped credentials (including invalid)
```

### File Descriptions

| File | Contents |
|------|----------|
| **xtream_valid.json** | Only credentials that passed `player_api.php` validation **and** are not expired. |
| **xtream_all.json** | Every credential that passed the extractor, regardless of validation status. |

Both files include:

- `domain`, `port`, `username`, `password`
- `xtream_url` (ready‑to‑use M3U link)
- `original_redirect` and `source_path`
- `user_info` (status, expiry, connections, etc.)

---

## 🎯 Example Workflow

```bash
python main.py
```

```
Enter your urlscan.io API key: 019a...

=== RUN CONFIGURATION ===
Select search query:
  1. page.url:"/live/play/"
  2. page.url:"/get.php?username="
  ...
  0. ALL OF THE ABOVE (OR-combined, 1-8)
> 2
Max scans to process [default: 50]
> 100
Maximum age of scans in days (1-365) [default: 30]
> 14
Validate credentials? [Y/n] (Y = validate all, n = skip validation)
> Y
```

The scraper will:

1. **Scrape** up to 100 scans from the last 14 days matching `/get.php?username=`.
2. **Validate** each credential in parallel (Rich progress bar).
3. **Export** `xtream_valid.json` and `xtream_all.json` into `output/YYYY-MM-DD_HH-MM-SS/`.

---

## 🛠️ Advanced Tips

- **Increase `max_scans`** for deeper crawls (capped at 500 to avoid API abuse).
- **Use short date windows** (e.g., 7 days) for higher hit rates.
- **Run multiple presets** sequentially to collect diverse panels.
- **Ctrl+C** during validation exits cleanly, keeping whatever was already validated.
- **Check `xtream_all.json`** for false positives or to debug extraction.

---

## 📄 License

This project is licensed under the MIT License — see the [LICENSE](https://raw.githubusercontent.com/kidpoleon/urlscan-public-xtream-scrape/refs/heads/main/LICENSE) file for details.

---

## 🤝 Contributing

Pull requests are welcome! For major changes, please open an issue first to discuss what you’d like to change.

---

## ⚠️ Disclaimer

This tool is for **educational and research purposes only**. The authors are not responsible for misuse.

---

**Happy scraping!** 🎉
