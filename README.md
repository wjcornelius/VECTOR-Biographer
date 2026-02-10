# VECTOR Biographer

**An AI that talks with you about your life and remembers everything.**

You talk. It listens. It asks good questions. Over time, it builds a complete picture of who you are - your stories, your people, your wisdom.

---

## System Requirements

- **Windows 10 or 11**
- **8GB RAM minimum** (16GB recommended)
- **5GB free disk space** (for AI models)
- **A microphone** (built-in laptop mic works fine)
- **Internet connection** (for the AI conversation, not for voice recognition)

---

## Getting Started

### Before You Start: Two Things You Need

**1. Python** (the programming language - free)
   - Go to https://www.python.org/downloads/
   - Click the big yellow "Download Python" button
   - Run the installer
   - **IMPORTANT: Check the box that says "Add Python to PATH"** (at the bottom of the first screen)
   - Click Install

**2. An Anthropic Account** (for the AI - pay as you go, about $1-2 per half hour of conversation)
   - Go to https://console.anthropic.com/
   - Click "Sign Up" and create an account
   - Add a payment method (Settings > Billing)
   - Click "API Keys" in the left sidebar
   - Click "Create Key"
   - Copy the key it gives you (starts with `sk-ant-...`) - you'll need this in a minute

---

### Installation (One Time)

1. **[Click here to download](https://github.com/wjcornelius/VECTOR-Biographer/archive/refs/heads/main.zip)**

2. Find the downloaded zip file and **unzip it** (right-click > Extract All)

3. Open the folder and **double-click `INSTALL.bat`**

4. When it asks for your API key, **paste it** (right-click > Paste) and press Enter

5. Wait. It downloads a lot of stuff. Could take 10 minutes. Let it run.

6. When it says "INSTALLATION COMPLETE", you're done!

---

### Running It

**Double-click "VECTOR Biographer" on your desktop.**

(If you don't see that shortcut, open the folder and double-click `START_BIOGRAPHER.bat` instead)

---

## How It Works

1. Click **Start**
2. It asks you a question (you'll hear it through your speakers)
3. **Talk into your microphone** - tell your story
4. When you're done talking, click **"I'M DONE"**
5. It thinks about what you said, saves the important parts, and asks another question
6. Keep going as long as you want
7. Click **End** when you're finished

**That's it.** Just talk to it like you'd talk to a friend.

---

## Tips

- **Speak naturally.** Tell stories. Go off on tangents. That's the good stuff.
- **Sessions can be any length.** 5 minutes or 2 hours.
- **Use Pause** if you need to step away.
- **It remembers everything** from previous sessions.

---

## If Something Goes Wrong

**"Python is not installed"**
You need to install Python first. See "Before You Start" above. Make sure you check "Add to PATH" during installation.

**Installation seems frozen**
It's probably still downloading. The AI models are big (~2GB). Give it 10-15 minutes.

**Can't hear anything / Microphone not working**
- Make sure your speakers aren't muted
- Check that your microphone is plugged in
- Windows Settings > Sound > make sure the right mic is selected

**"API key invalid"**
Your key might have a typo. Open the `.env` file in Notepad and check it. The key should start with `sk-ant-`.

**Something else broke**
Try running `INSTALL.bat` again. It won't hurt anything.

---

## What Does It Cost?

The AI (Claude, made by Anthropic) charges based on usage:
- **About $1-2 per 30 minutes of conversation**
- You can check your balance at console.anthropic.com
- Add money to your account as needed

---

## Questions?

**What is this, really?**
It's a voice-based AI interviewer that helps you tell your life story. It asks questions, listens to your answers, and builds a searchable database of everything you share.

**Why would I want this?**
To capture who you are - not just facts, but how you think, what you've learned, who shaped you. For yourself, for your family, for whoever comes after.

**Is my data private?**
Your voice is transcribed locally on your computer - the audio never leaves your machine. Only the text of what you said goes to Anthropic for the AI to respond. Your database stays entirely on your computer.

**Can I see what it's captured?**
Yes! Click the visualization buttons in the app to see your memories mapped out.

---

*Built by a human and Claude, February 2026.*

*"I'm not trying to live forever. I'm trying to create a seed that could grow into something new."*
