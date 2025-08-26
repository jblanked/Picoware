#pragma once
#include "../../../system/view.hpp"
#include "../../../system/view_manager.hpp"
#include "../../../gui/textbox.hpp"
#include "../../../applications/applications/flip_social/utils.hpp"

static TextBox *flipSocialFeedTextBox = nullptr;
static bool flipSocialFeedRequested = true;
static int flipSocialSeriesIndex = 1;
static int flipSocialMaxSeriesIndex = 10; // no more than 10 series ~ 100 feed posts
static int flipSocialLastFeedIndex = 0;
static String flipSocialFeedText = "";

static void flipSocialAppendFeedItem(TextBox *textbox, const char *username, const char *message, const char *dateCreated)
{
    // Append new item to the persistent string
    if (flipSocialFeedText.length() > 0)
    {
        flipSocialFeedText += "\n\n";
    }

    flipSocialFeedText += username + String(" - ") + dateCreated + String(":\n") + message;

    // Update the textbox with the new content
    textbox->setCurrentText(flipSocialFeedText.c_str());
}

static bool flipSocialFeedStart(ViewManager *viewManager)
{
    if (flipSocialFeedTextBox)
    {
        delete flipSocialFeedTextBox;
        flipSocialFeedTextBox = nullptr;
    }

    // Clear the feed text for new content
    flipSocialFeedText = "";

    auto draw = viewManager->getDraw();
    flipSocialFeedTextBox = new TextBox(
        draw,
        0,
        320,
        viewManager->getForegroundColor(),
        viewManager->getBackgroundColor(),
        true // show scrollbar
    );
    draw->text(Vector(5, 5), "Fetching Feed...");
    draw->swap();
    return true; // return true to indicate the start was successful.
}

static void flipSocialFeedRun(ViewManager *viewManager)
{
    auto inputManager = viewManager->getInputManager();
    auto input = inputManager->getLastButton();
    switch (input)
    {
    case BUTTON_BACK:
        viewManager->back();
        inputManager->reset(true);
        return;
    case BUTTON_RIGHT:
    case BUTTON_CENTER:
    {
        flipSocialFeedRequested = true;
        auto draw = viewManager->getDraw();
        draw->clear(Vector(0, 0), viewManager->getSize(), viewManager->getBackgroundColor());
        draw->text(Vector(5, 5), "Fetching Feed...");
        draw->swap();
        flipSocialLastFeedIndex = flipSocialFeedTextBox->getCurrentLine() + flipSocialFeedTextBox->getLinesPerScreen() - 1;
        inputManager->reset(true);
    }
    break;
    case BUTTON_UP:
        if (flipSocialFeedTextBox)
        {
            flipSocialFeedTextBox->scrollUp();
            inputManager->reset(true);
        }
        break;
    case BUTTON_DOWN:
        if (flipSocialFeedTextBox)
        {
            flipSocialFeedTextBox->scrollDown();
            inputManager->reset(true);
            auto index = flipSocialFeedTextBox->getCurrentLine();
            if (index == flipSocialFeedTextBox->getTotalLines() - 1 && flipSocialSeriesIndex < flipSocialMaxSeriesIndex)
            {
                // If we are at the bottom of the feed, request a new feed
                flipSocialFeedRequested = true;
                auto draw = viewManager->getDraw();
                draw->clear(Vector(0, 0), viewManager->getSize(), viewManager->getBackgroundColor());
                draw->text(Vector(5, 5), "Fetching Feed...");
                draw->swap();
                flipSocialLastFeedIndex = index + flipSocialFeedTextBox->getLinesPerScreen() - 1;
            }
        }
        break;
    default:
        break;
    }
    if (flipSocialFeedRequested)
    {
        flipSocialFeedRequested = false;
        String user = flipSocialUtilsLoadUserFromFlash(viewManager);
        auto draw = viewManager->getDraw();
        int series_index = flipSocialSeriesIndex;
        String url = "https://www.jblanked.com/flipper/api/feed/10/" + user + "/" + std::to_string(series_index) + "/max/series/";
        auto response = flipSocialHttpRequest(viewManager, "GET", url);
        if (response == "")
        {
            draw->clear(Vector(0, 0), viewManager->getSize(), viewManager->getBackgroundColor());
            draw->text(Vector(5, 5), "Error fetching feed.");
            draw->swap();
            delay(2000);
            return;
        }
        // append each item to the textbox
        for (int i = 0; i < 10; i++)
        {
            String item = getJsonArrayValue(response.c_str(), "feed", i);
            if (item != "")
            {
                String username = getJsonValue(item.c_str(), "username");
                String message = getJsonValue(item.c_str(), "message");
                String dateCreated = getJsonValue(item.c_str(), "date_created");
                flipSocialAppendFeedItem(flipSocialFeedTextBox, username.c_str(), message.c_str(), dateCreated.c_str());
            }
        }

        // Update and render the textbox with the final text
        flipSocialFeedTextBox->setText(flipSocialFeedText.c_str());
        if (flipSocialSeriesIndex == 1)
        {
            flipSocialLastFeedIndex = flipSocialFeedTextBox->getLinesPerScreen() - 1;
            flipSocialFeedTextBox->setCurrentLine(flipSocialLastFeedIndex); // Start at the bottom of the feed
        }
        else
        {
            // start where the user left off
            flipSocialFeedTextBox->setCurrentLine(flipSocialLastFeedIndex);
        }
        flipSocialSeriesIndex++;
    }
}

static void flipSocialFeedStop(ViewManager *viewManager)
{
    flipSocialFeedRequested = true;
    flipSocialFeedText = "";
    flipSocialSeriesIndex = 1;
    if (flipSocialFeedTextBox)
    {
        delete flipSocialFeedTextBox;
        flipSocialFeedTextBox = nullptr;
    }
}

static const View flipSocialFeedView = View("FlipSocialFeed", flipSocialFeedRun, flipSocialFeedStart, flipSocialFeedStop);