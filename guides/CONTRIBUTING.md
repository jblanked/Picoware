# Contributing to Picoware

This guide explains how to contribute to Picoware, whether it's an app, documentation, or firmware. The only requirement to contribute is that you have a GitHub account.

## Table of Contents
- [Issues](#issues)
- [Feature Requests](#feature-requests)
- [Contributing (Online)](#contributing-online)
- [Contributing (Command Line)](#contributing-command-line)

## Issues
If you find a bug or are having trouble with something, you can create an issue on the [Picoware GitHub repository](https://github.com/jblanked/Picoware/issues). When creating an issue, please provide as much detail as possible, including steps to reproduce the issue, screenshots, and any relevant information about your setup.

## Feature Requests
If you have an idea for a new feature or improvement, you can create a discussion on the [Picoware GitHub repository](https://github.com/jblanked/Picoware/discussions). When creating a discussion, please provide a clear description of your idea and how it would benefit users.

## Contributing (Online)
If you want to contribute code, documentation, or other resources, you'll need to fork the repository, make your changes, and then create a pull request to the `dev` branch. You can do this through github.com by clicking the "Fork" button on the repository page. Once forked, make your changes on a new branch (not `main`) in your forked repository, then click "New Pull Request" and make sure to select the `dev` branch as the base branch before submitting your changes for review.

## Contributing (Command Line)
Alternatively, you can use Git on the command line to fork the repository, make your changes, and push them to your forked repository before creating a pull request.

### Cloning the Repository
To clone the repository, you can use the following command:
```bash
git clone https://github.com/jblanked/Picoware.git
```

### Creating a Branch
To create a new branch for your changes, use the following command:
```bash
git checkout -b your-branch-name
```

> [!NOTE]
> Replace `your-branch-name` with a descriptive name for your branch that reflects the changes you are making.

### Committing Changes
After making your changes, you can commit them with the following commands:
```bash
git add .
git commit -m "Your commit message"
```

> [!NOTE]
> Replace `Your commit message` with a clear and concise message that describes the changes you have made.

### Pushing Changes
To push your changes to your forked repository, use the following command:
```bash
git push origin your-branch-name
```

> [!NOTE]
> `your-branch-name` should be the same as the branch name you created earlier.

### Creating a Pull Request
After pushing your changes, you can create a pull request on GitHub by navigating to your forked repository and clicking the "New Pull Request" button. Make sure to select the `dev` branch as the base branch for your pull request.

Once you have created your pull request, it will be reviewed by JBlanked typically within a few days. If your changes are approved, they will be merged into the `dev` branch and eventually into the main branch for release.