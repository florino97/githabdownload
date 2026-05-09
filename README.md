# githubdownload

Greetings.

This bot is used for uploading files from Telegram to GitHub.
And also, this bot receives a direct download link of a file, downloads and uploads it to your GitHub, and you can download it from your GitHub.
Very simply summarized:

Its working method is as follows:

1. We **Fork** a specific project on GitHub (meaning we make a copy of it in our own account).
2. We configure it once so that **GitHub Actions** gets activated.
3. After that, whenever we want to download a file:
* We edit the `README.md` file.
* In the **commit message**, we write this:
: direct link of the file

4. GitHub itself downloads that file on its servers.
5. The downloaded file is placed inside the `downloads/` folder in your repository.
6. Then we can download the entire repository as a ZIP and get the file.

Usage:

* Downloading files that do not open directly with the domestic internet, for now that the national internet is accessible.
* Now it also supports Twitter, YouTube, Google Play, and other links, of course by using this repo
[http://github.com/iphoenixon/youtube-sandbox](http://github.com/iphoenixon/youtube-sandbox)

Note: Because GitHub has a storage limit, sometimes we have to delete the repository and Fork it again.

Now, this Telegram bot does exactly this job automatically.

Commands to run the bot on your server:

Note: Inside the bot's code, meaning the gitwaydownloader.py file, in the first lines of the code, replace your Telegram bot token and your own numeric ID.

First, you must install the prerequisites:

pip install -r requirements.txt

Then we run the bot:

python gitwaydownloader.py

Done.

In-bot guide:
With the /start command, the bot gives the reference repository link to the user and asks them to Fork it. Then it requests a GitHub token (PAT).
(A default repository link has been placed)

After sending the GitHub token (PAT), the bot asks for the name of the repository where the downloads are supposed to be saved.
(in the username/repo format).
Here it means that same forked repository of your own account.

By sending this information, the user's account is connected.

Remaining commands:

/setup command:
If a user wants to change/update their token or repository name, they use this command.
/cancel command: While entering the token or repository information, if the user changes their mind, the operation is stopped with this command.
File management (/files): The user can see the list of all downloaded files inside the GitHub folder directly within Telegram.

Delete file (/delete): With the /delete filename.mp4 command, the user can delete large files so the GitHub account storage does not get full.

Check storage status (/status): Display the consumed storage of the user's repository.

Smart link shortener (/shorten): GitHub Raw links are very long. By turning on this feature, the bot automatically delivers a short download link (TinyUrl).

Send file (upload): Whatever file (photo, video, file, etc.) the user sends to the bot, the bot uploads it in the downloads folder of their GitHub repository and delivers its link.

Downloading process from a link:
The user sends a text link to the bot. The bot makes a commit on the README.md file in the user's GitHub with the message download:  so that GitHub Actions downloads the file in the background and places it in the repository.

Bot admin commands:
/stats command:
Shows the total number of users who have registered in the bot (entered a token).
/broadcast  command: Sends the message you write after this command as a broadcast message to all users of the bot.

/settemplate <new_link> command:
If the address of the reference repository that you want users to fork changes, you change the default link inside the /start message with this command. (Example: /settemplate [http://github.com/iphoenixon/youtube-sandbox](http://github.com/iphoenixon/youtube-sandbox))

Ban/unban system: For the admin (/ban user_id and /unban user_id).

Steps to get your GitHub token:

Log into your account on GitHub.
From the top right corner, click on your profile picture and select Settings.
In the left menu, scroll down and click on Developer settings.
From the left menu, click on Personal access tokens and then Tokens (classic).
Click on the Generate new token (classic) button.
In the Note section, write a desired name for the token.
In the Select scopes section, check the repo option (for full access to repositories).
Go to the bottom of the page and click on Generate token.
Copy the generated token (this token is shown to you only this one time).

Necessary notes:

Although this bot is designed so that it can be used publicly, please do not use your main GitHub account token under any circumstances, there is a risk of getting banned or even others gaining access to your account,
If you want to use the project, run it yourself on your own server.

Windows installer version project, without a server and completely offline:

First, download and extract the x_fetch_client_windows_x86 file from the releases section and run the installer file.

This installation file does not need a server. You paste your GitHub token into the specified field.
Then you fork the following repo:

[http://github.com/iphoenixon/youtube-sandbox](http://github.com/iphoenixon/youtube-sandbox)

Then go inside your own repository on GitHub
The same one you forked that is copied into your own repository,
go there
Go to:
Settings → Actions → General
Find the Workflow permissions section
Select the following option:
Read and write permissions
Click on Save

And then go into the Actions section of your fork (the same repo you forked) and click on that green button to give permission for GitHub Actions to start working.

Now enter the program and paste that fork link in your own repository with the following format:

USERNAME/youtube-sandbox

Now for YouTube, according to the descriptions of the forked project itself, we need to get a session:

Steps:
In the browser (preferably incognito mode), log into YouTube with your account.
Install the Get cookies.txt LOCALLY extension.
Click on the extension icon and click Export so that the cookies.txt file gets downloaded.
Go to Settings → Secrets and variables → Actions
Click on New repository secret.
Name the Secret: YOUTUBE_COOKIES
Paste the entire content of the cookies.txt file into the Secret section and save it.
Done

Now in the program, give it the YouTube, Twitter, Spotify, etc. link and send it to GitHub and done, wait for it to be downloaded.
Then refresh the downloads list and save it.

It works better for small files, although it also divides large files into several parts.
And try to always empty and delete the downloads inside the repo.

Thanks to dear Sarto for this interesting idea,

And also the developer of the following project:
[http://github.com/iphoenixon/youtube-sandbox](http://github.com/iphoenixon/youtube-sandbox)

Please give the project a star to support us.

Telegram channel:
@eots1
