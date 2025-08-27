#include "../../../applications/applications/flip_social/run.hpp"
#include "../../../applications/applications/flip_social/utils.hpp"

#define MAX_PRE_SAVED_MESSAGES 20 // Maximum number of pre-saved messages
#define MAX_MESSAGE_LENGTH 100    // Maximum length of a message in the feed
#define MAX_EXPLORE_USERS 50      // Maximum number of users to explore
#define MAX_USER_LENGTH 32        // Maximum length of a username
#define MAX_FRIENDS 50            // Maximum number of friends
#define MAX_FEED_ITEMS 25         // Maximum number of feed items
#define MAX_MESSAGE_USERS 40      // Maximum number of users to display in the submenu
#define MAX_MESSAGES 20           // Maximum number of messages between each user
#define MAX_COMMENTS 20           // Maximum number of comments per feed item

#define FLIP_SOCIAL_LOGIN_PATH FLIP_SOCIAL_DIRECTORY "/login.json"                     // picoware/flip_social/login.json
#define FLIP_SOCIAL_PRESAVES_PATH FLIP_SOCIAL_DIRECTORY "/presaves.txt"                // picoware/flip_social/presaves.txt
#define FLIP_SOCIAL_EXPLORE_LIST_PATH FLIP_SOCIAL_DIRECTORY "/explore.json"            // picoware/flip_social/explore.json
#define FLIP_SOCIAL_EXPLORE_USER_PATH FLIP_SOCIAL_DIRECTORY "/explore_user.json"       // picoware/flip_social/explore_user.json
#define FLIP_SOCIAL_MESSAGE_USER_LIST_PATH FLIP_SOCIAL_DIRECTORY "/message_user.json"  // picoware/flip_social/message_user.json
#define FLIP_SOCIAL_PROFILE_PATH FLIP_SOCIAL_DIRECTORY "/profile.json"                 // picoware/flip_social/profile.json
#define FLIP_SOCIAL_MESSAGE_TO_USER_PATH FLIP_SOCIAL_DIRECTORY "/message_to_user.json" // picoware/flip_social/message_to_user.json
#define FLIP_SOCIAL_NEW_POST_PATH FLIP_SOCIAL_DIRECTORY "/new_post.json"               // picoware/flip_social/new_post.json
#define FLIP_SOCIAL_COMMENT_POST_PATH FLIP_SOCIAL_DIRECTORY "/comment_post.json"       // picoware/flip_social/comment_post.json

FlipSocialRun::FlipSocialRun(ViewManager *viewManager) : commentsIndex(0), commentIsValid(false), commentItemID(0), commentsStatus(CommentsNotStarted),
                                                         currentMenuIndex(SocialViewFeed), currentProfileElement(ProfileElementBio), currentView(SocialViewLogin),
                                                         exploreIndex(0), exploreStatus(ExploreKeyboardUsers),
                                                         feedItemID(0), feedItemIndex(0), feedIteration(1), feedStatus(FeedNotStarted), inputHeld(false), lastInput(-1),
                                                         loginStatus(LoginNotStarted), messagesStatus(MessagesNotStarted), messageUsersStatus(MessageUsersNotStarted), messageUserIndex(0),
                                                         postStatus(PostChoose), registrationStatus(RegistrationNotStarted),
                                                         shouldDebounce(false), shouldReturnToMenu(false), userInfoStatus(UserInfoNotStarted),
                                                         viewManager(viewManager)
{
    char *loginStatusStr = (char *)malloc(64);
    if (loginStatusStr)
    {
        auto storage = viewManager->getStorage();
        size_t bytes_read = 0;
        if (!storage.read(FLIP_SOCIAL_LOGIN_PATH, loginStatusStr, 64, &bytes_read))
        {
            printf("Failed to load login status.\n");
            free(loginStatusStr);
            return;
        }
        loginStatusStr[bytes_read] = '\0'; // Ensure null termination at actual read length
        if (strcmp(loginStatusStr, "success") == 0)
        {
            loginStatus = LoginSuccess;
            currentView = SocialViewMenu;
        }
        else
        {
            loginStatus = LoginNotStarted;
            currentView = SocialViewLogin;
        }
        free(loginStatusStr);
    }
}

FlipSocialRun::~FlipSocialRun()
{
    loading.reset();
    loading = nullptr;
    http.reset();
    http = nullptr;
}

void FlipSocialRun::debounceInput()
{
    static uint8_t debounceCounter = 0;
    if (shouldDebounce)
    {
        lastInput = -1;
        debounceCounter++;
        if (debounceCounter < 2)
        {
            return;
        }
        debounceCounter = 0;
        shouldDebounce = false;
        inputHeld = false;
    }
}

void FlipSocialRun::drawCommentsView(Canvas *canvas)
{
    static bool loadingStarted = false;
    switch (commentsStatus)
    {
    case CommentsWaiting:
        if (!loadingStarted)
        {
            if (!loading)
            {
                loading = std::make_unique<Loading>(canvas);
            }
            loadingStarted = true;
            if (loading)
            {
                loading->setText("Fetching...");
            }
        }
        if (!this->httpRequestIsFinished())
        {
            if (loading)
            {
                loading->animate(false);
            }
            else
            {
                loading = std::make_unique<Loading>(canvas);
            }
            if (http)
            {
                http->update(); // poll async
            }
        }
        else
        {
            if (!http || http->getState() == ISSUE || http->getAsyncResponse().empty())
            {
                commentsStatus = CommentsRequestError;
                feedStatus = FeedRequestError;
                if (loading)
                {
                    loading->stop();
                }
                loadingStarted = false;
                return;
            }

            commentsStatus = CommentsSuccess;
            if (loading)
            {
                loading->stop();
            }
            loadingStarted = false;
        }
        break;
    case CommentsSuccess:
    {
        if (http)
        {
            std::string response = http->getAsyncResponse();
            if (strstr(response.c_str(), "\"comments\":[{") != NULL)
            {
                commentIsValid = true;
                // Count total comments first
                int total_comments = 0;
                for (int j = 0; j < MAX_COMMENTS; j++)
                {
                    std::string tempComment = getJsonArrayValue(response.c_str(), "comments", j);
                    if (!tempComment.empty())
                    {
                        total_comments++;
                    }
                    else
                    {
                        break;
                    }
                }

                // Parse the comments array and display the current comment at commentsIndex
                for (int i = 0; i < MAX_COMMENTS; i++)
                {
                    if (i != commentsIndex)
                    {
                        continue; // only draw the current displayed comment
                    }
                    // Get the specific comment at the current index
                    std::string commentItem = getJsonArrayValue(response.c_str(), "comments", i);
                    if (!commentItem.empty())
                    {
                        std::string username = getJsonValue(commentItem.c_str(), "username");
                        std::string message = getJsonValue(commentItem.c_str(), "message");
                        std::string flipped = getJsonValue(commentItem.c_str(), "flipped");
                        std::string flips_str = getJsonValue(commentItem.c_str(), "flip_count");
                        std::string date_created = getJsonValue(commentItem.c_str(), "date_created");
                        std::string id_str = getJsonValue(commentItem.c_str(), "id");
                        if (username.empty() || message.empty() || flipped.empty() || flips_str.empty() || date_created.empty() || id_str.empty())
                        {
                            commentsStatus = CommentsParseError;
                            return;
                        }
                        commentItemID = std::stoi(id_str);
                        drawFeedItem(canvas, username, message, flipped, flips_str, date_created);

                        // Draw navigation arrows if there are multiple comments
                        canvas_set_font_custom(canvas, FONT_SIZE_SMALL);
                        if (commentsIndex > 0)
                        {
                            canvas_draw_str(canvas, 2, 60, "< Prev");
                        }
                        if (commentsIndex < (total_comments - 1))
                        {
                            canvas_draw_str(canvas, 96, 60, "Next >");
                        }

                        // Draw comment counter
                        char comment_counter[32];
                        snprintf(comment_counter, sizeof(comment_counter), "%d/%d", commentsIndex + 1, total_comments);
                        canvas_draw_str(canvas, 112, 10, comment_counter);

                        break; // Exit the loop after drawing the current comment
                    }
                    else
                    {
                        // If current comment index doesn't exist, go back to previous
                        if (commentsIndex > 0)
                        {
                            commentsIndex--;
                        }
                        break;
                    }
                }
            }
            else
            {
                canvas_set_font_custom(canvas, FONT_SIZE_SMALL);
                canvas_draw_str(canvas, 0, 10, "No comments found for this post.");
                canvas_draw_str(canvas, 0, 60, "Be the first, click DOWN");
            }
        }
        break;
    }
    case CommentsRequestError:
        canvas_clear(canvas);
        canvas_set_font(canvas, FontPrimary);
        canvas_draw_str(canvas, 0, 10, "Comments request failed!");
        canvas_draw_str(canvas, 0, 20, "Check your network and");
        canvas_draw_str(canvas, 0, 30, "try again later.");
        break;
    case CommentsParseError:
        canvas_clear(canvas);
        canvas_set_font(canvas, FontPrimary);
        canvas_draw_str(canvas, 0, 10, "Failed to parse comments!");
        canvas_draw_str(canvas, 0, 20, "Try again...");
        break;
    case CommentsNotStarted:
        canvas_clear(canvas);
        commentsStatus = CommentsWaiting;
        userRequest(RequestTypeCommentFetch);
        break;
    case CommentsKeyboard:
    {
        auto keyboard = viewManager->getKeyboard();
        if (keyboard)
        {
            keyboard->run(false);
        }
        break;
    }
    case CommentsSending:
        if (!loadingStarted)
        {
            if (!loading)
            {
                loading = std::make_unique<Loading>(canvas);
            }
            loadingStarted = true;
            if (loading)
            {
                loading->setText("Sending...");
            }
        }
        if (!this->httpRequestIsFinished())
        {
            if (loading)
            {
                loading->animate(false);
            }
            else
            {
                loading = std::make_unique<Loading>(canvas);
            }
            if (http)
            {
                http->update(); // poll async
            }
        }
        else
        {
            if (loading)
            {
                loading->stop();
            }
            loadingStarted = false;
            if (!http || http->getState() == ISSUE)
            {
                commentsStatus = CommentsRequestError;
                return;
            }
            if (http->getAsyncResponse().find("[SUCCESS]") != std::string::npos)
            {
                currentView = SocialViewFeed;
                currentMenuIndex = SocialViewFeed;
                commentsStatus = CommentsNotStarted;
                feedStatus = FeedNotStarted;
                feedItemIndex = 0;
                feedIteration = 1;
                return;
            }
            else
            {
                commentsStatus = CommentsRequestError;
            }
        }
        break;
    default:
        canvas_clear(canvas);
        canvas_set_font(canvas, FontPrimary);
        canvas_draw_str(canvas, 0, 10, "Loading comments...");
        break;
    }
}

void FlipSocialRun::drawExploreView(Canvas *canvas)
{
    canvas_clear(canvas);
    canvas_set_font(canvas, FontPrimary);
    static bool loadingStarted = false;
    switch (exploreStatus)
    {
    case ExploreWaiting:
        if (!loadingStarted)
        {
            if (!loading)
            {
                loading = std::make_unique<Loading>(canvas);
            }
            loadingStarted = true;
            if (loading)
            {
                loading->setText("Searching...");
            }
        }
        if (!this->httpRequestIsFinished())
        {
            if (loading)
            {
                loading->animate(false);
            }
            else
            {
                loading = std::make_unique<Loading>(canvas);
            }
            if (http)
            {
                http->update(); // poll async
            }
        }
        else
        {
            if (loading)
            {
                loading->stop();
            }
            loadingStarted = false;
            if (!http || http->getState() == ISSUE)
            {
                exploreStatus = ExploreRequestError;
                return;
            }
            auto response = http->getAsyncResponse();
            if (response.find("users") != std::string::npos)
            {
                exploreStatus = ExploreSuccess;
                auto storage = viewManager->getStorage();
                if (!storage.write(FLIP_SOCIAL_EXPLORE_LIST_PATH, response.c_str(), response.size()))
                {
                    printf("Failed to save explore user list to storage.\n");
                    exploreStatus = ExploreParseError;
                }
                return;
            }
            else
            {
                exploreStatus = ExploreRequestError;
            }
        }
        break;
    case ExploreSuccess:
    {
        canvas_draw_str(canvas, 0, 10, "Explore success!");
        canvas_draw_str(canvas, 0, 20, "Press OK to continue.");

        if (!http)
        {
            printf("drawExploreView: Failed to load explore data from storage\n");
            canvas_draw_str(canvas, 0, 30, "Failed to load explore data.");
            return;
        }

        char *exploreUsers = (char *)malloc(1024);
        if (!exploreUsers)
        {
            printf("Failed to allocate memory for explore users.\n");
            canvas_draw_str(canvas, 0, 30, "Failed to load explore data.");
            return;
        }

        auto storage = viewManager->getStorage();
        size_t bytes_read = 0;
        if (!storage.read(FLIP_SOCIAL_EXPLORE_LIST_PATH, exploreUsers, 1024, &bytes_read))
        {
            printf("Failed to read explore user list from storage.\n");
            canvas_draw_str(canvas, 0, 30, "Failed to load explore data.");
            free(exploreUsers);
            return;
        }
        exploreUsers[bytes_read] = '\0'; // Ensure null termination at actual read length

        // store users
        std::vector<std::string> usersList;
        for (int i = 0; i < MAX_EXPLORE_USERS; i++)
        {
            std::string user = getJsonArrayValue(exploreUsers, "users", i);
            if (user.empty())
            {
                break; // No more users in the list
            }
            usersList.push_back(user);
        }

        if (usersList.empty())
        {
            canvas_draw_str(canvas, 0, 30, "No users found.");
        }
        else
        {
            // std::vector<std::string> to const char** for drawMenu
            std::vector<const char *> userPtrs;
            userPtrs.reserve(usersList.size());
            for (const auto &user : usersList)
            {
                userPtrs.push_back(user.c_str());
            }
            drawMenu(canvas, exploreIndex, userPtrs.data(), userPtrs.size());
        }
        free(exploreUsers);
        break;
    }
    case ExploreRequestError:
        canvas_draw_str(canvas, 0, 10, "Messages request failed!");
        canvas_draw_str(canvas, 0, 20, "Check your network and");
        canvas_draw_str(canvas, 0, 30, "try again later.");
        break;
    case ExploreParseError:
        canvas_draw_str(canvas, 0, 10, "Error parsing messages!");
        canvas_draw_str(canvas, 0, 20, "Please set your username");
        canvas_draw_str(canvas, 0, 30, "and password in the app.");
        break;
    case ExploreNotStarted:
        exploreStatus = ExploreWaiting;
        userRequest(RequestTypeExplore);
        break;
    case ExploreKeyboardUsers:
    {
        auto keyboard = viewManager->getKeyboard();
        if (keyboard)
        {
            keyboard->run(false);
        }
        break;
    }
    case ExploreKeyboardMessage:
    {
        auto keyboard = viewManager->getKeyboard();
        if (keyboard)
        {
            keyboard->run(false);
        }
        break;
    }
    case ExploreSending:
        if (!loadingStarted)
        {
            if (!loading)
            {
                loading = std::make_unique<Loading>(canvas);
            }
            loadingStarted = true;
            if (loading)
            {
                loading->setText("Sending...");
            }
        }
        if (!this->httpRequestIsFinished())
        {
            if (loading)
            {
                loading->animate(false);
            }
            else
            {
                loading = std::make_unique<Loading>(canvas);
            }
            if (http)
            {
                http->update(); // poll async
            }
        }
        else
        {
            if (loading)
            {
                loading->stop();
            }
            loadingStarted = false;
            if (!http || http->getState() == ISSUE)
            {
                exploreStatus = ExploreRequestError;
                return;
            }
            if (http->getAsyncResponse().find("[SUCCESS]") != std::string::npos)
            {
                currentView = SocialViewMessageUsers;
                currentMenuIndex = SocialViewMessageUsers;
                messageUsersStatus = MessageUsersNotStarted;
                exploreStatus = ExploreKeyboardUsers;
                exploreIndex = 0;
                if (viewManager->getKeyboard())
                {
                    viewManager->getKeyboard()->reset();
                }
                return;
            }
            else
            {
                exploreStatus = ExploreRequestError;
            }
        }
        break;
    default:
        canvas_draw_str(canvas, 0, 10, "Retrieving messages...");
        break;
    }
}

void FlipSocialRun::drawFeedItem(Canvas *canvas, String username, String message, String flipped, String flips, String date_created)
{
    bool isFlipped = flipped == "true";
    auto flipCount = std::stoi(flips);
    canvas_clear(canvas);
    canvas_set_font_custom(canvas, FONT_SIZE_LARGE);
    canvas_draw_str(canvas, 0, 18, username.c_str());
    canvas_set_font_custom(canvas, FONT_SIZE_MEDIUM);
    drawFeedMessage(canvas, message.c_str(), 0, 30);
    canvas_set_font_custom(canvas, FONT_SIZE_SMALL);
    char flip_message[32];
    snprintf(flip_message, sizeof(flip_message), "%u %s", flipCount, flipCount == 1 ? "flip" : "flips");
    canvas_draw_str(canvas, 0, 150, flip_message);
    // canvas_draw_icon(canvas, 35, 54, &I_ButtonOK_7x7);
    char flip_status[16];
    snprintf(flip_status, sizeof(flip_status), isFlipped ? "Unflip" : "Flip");
    canvas_draw_str(canvas, isFlipped ? 110 : 115, 150, flip_status);
    if (strstr(date_created.c_str(), "minutes ago") == NULL)
    {
        canvas_draw_str(canvas, 190, 150, date_created.c_str());
    }
    else
    {
        canvas_draw_str(canvas, 180, 150, date_created.c_str());
    }
}

void FlipSocialRun::drawFeedMessage(Canvas *canvas, const char *user_message, int x, int y)
{
    if (!user_message)
    {
        printf("User message is NULL.\n");
        return;
    }

    // We will read through user_message and extract words manually
    const char *p = user_message;

    // Skip leading spaces
    while (*p == ' ')
        p++;

    char line[128];
    size_t line_len = 0;
    line[0] = '\0';
    int line_num = 0;

    while (*p && line_num < 6)
    {
        // Find the end of the next word
        const char *word_start = p;
        while (*p && *p != ' ')
            p++;
        size_t word_len = p - word_start;

        // Extract the word into a temporary buffer
        char word[128];
        if (word_len > 127)
        {
            word_len = 127; // Just to avoid overflow if extremely large
        }
        memcpy(word, word_start, word_len);
        word[word_len] = '\0';

        // Skip trailing spaces for the next iteration
        while (*p == ' ')
            p++;

        if (word_len == 0)
        {
            // Empty word (consecutive spaces?), just continue
            continue;
        }

        // Check how the word fits into the current line
        char test_line[256];
        if (line_len == 0)
        {
            // If line is empty, the line would just be this word
            strncpy(test_line, word, sizeof(test_line) - 1);
            test_line[sizeof(test_line) - 1] = '\0';
        }
        else
        {
            // If not empty, we add a space and then the word
            snprintf(test_line, sizeof(test_line), "%s %s", line, word);
        }

        uint16_t width = canvas_string_width(canvas, test_line);
        if (width <= 320)
        {
            // The word fits on this line
            strcpy(line, test_line);
            line_len = strlen(line);
        }
        else
        {
            // The word doesn't fit on this line
            // First, draw the current line if it's not empty
            if (line_len > 0)
            {
                canvas_draw_str_aligned(canvas, x, y + line_num * 20, AlignLeft, AlignTop, line);
                line_num++;
                if (line_num >= 6)
                    break;
            }

            // Now we try to put the current word on a new line
            // Check if the word itself fits on an empty line
            width = canvas_string_width(canvas, word);
            if (width <= 320)
            {
                // The whole word fits on a new line
                strcpy(line, word);
                line_len = word_len;
            }
            else
            {
                // The word alone doesn't fit. We must truncate it.
                // We'll find the largest substring of the word that fits.
                size_t truncate_len = word_len;
                while (truncate_len > 0)
                {
                    char truncated[128];
                    strncpy(truncated, word, truncate_len);
                    truncated[truncate_len] = '\0';
                    if (canvas_string_width(canvas, truncated) <= 320)
                    {
                        // Found a substring that fits
                        strcpy(line, truncated);
                        line_len = truncate_len;
                        break;
                    }
                    truncate_len--;
                }

                if (line_len == 0)
                {
                    // Could not fit a single character. Skip this word.
                }
            }
        }
    }

    // Draw any remaining text in the buffer if we have lines left
    if (line_len > 0 && line_num < 6)
    {
        canvas_draw_str_aligned(canvas, x, y + line_num * 20, AlignLeft, AlignTop, line);
    }
}

void FlipSocialRun::drawFeedView(Canvas *canvas)
{
    static bool loadingStarted = false;
    switch (feedStatus)
    {
    case FeedWaiting:
        if (!loadingStarted)
        {
            if (!loading)
            {
                loading = std::make_unique<Loading>(canvas);
            }
            loadingStarted = true;
            if (loading)
            {
                loading->setText("Fetching...");
            }
        }
        if (!this->httpRequestIsFinished())
        {
            if (loading)
            {
                loading->animate(false);
            }
            else
            {
                loading = std::make_unique<Loading>(canvas);
            }
            if (http)
            {
                http->update(); // poll async
            }
        }
        else
        {
            if (!http || http->getState() == ISSUE)
            {
                feedStatus = FeedRequestError;
                if (loading)
                {
                    loading->stop();
                }
                loadingStarted = false;
                return;
            }
            if (!http->getAsyncResponse().empty())
            {
                feedStatus = FeedSuccess;
                if (loading)
                {
                    loading->stop();
                }
                loadingStarted = false;
                return;
            }
            feedStatus = FeedRequestError;
        }
        break;
    case FeedSuccess:
    {
        if (http && !http->getAsyncResponse().empty())
        {
            for (int i = 0; i < MAX_FEED_ITEMS; i++)
            {
                if (i != feedItemIndex)
                {
                    continue;
                }
                // only draw the current displayed feed item
                std::string feedItem = getJsonArrayValue(http->getAsyncResponse().c_str(), "feed", i);
                if (!feedItem.empty())
                {
                    std::string username = getJsonValue(feedItem.c_str(), "username");
                    std::string message = getJsonValue(feedItem.c_str(), "message");
                    std::string flipped = getJsonValue(feedItem.c_str(), "flipped");
                    std::string flips_str = getJsonValue(feedItem.c_str(), "flip_count");
                    std::string date_created = getJsonValue(feedItem.c_str(), "date_created");
                    std::string id_str = getJsonValue(feedItem.c_str(), "id");
                    if (username.empty() || message.empty() || flipped.empty() || flips_str.empty() || date_created.empty() || id_str.empty())
                    {
                        feedStatus = FeedParseError;
                        return;
                    }
                    feedItemID = std::stoi(id_str);
                    drawFeedItem(canvas, username, message, flipped, flips_str, date_created);
                }
            }
        }
        break;
    }
    case FeedRequestError:
        canvas_clear(canvas);
        canvas_set_font(canvas, FontPrimary);
        canvas_draw_str(canvas, 0, 10, "Feed request failed!");
        canvas_draw_str(canvas, 0, 20, "Check your network and");
        canvas_draw_str(canvas, 0, 30, "try again later.");
        break;
    case FeedParseError:
        canvas_clear(canvas);
        canvas_set_font(canvas, FontPrimary);
        canvas_draw_str(canvas, 0, 10, "Failed to parse feed!");
        canvas_draw_str(canvas, 0, 20, "Try again...");
        break;
    case FeedNotStarted:
        canvas_clear(canvas);
        feedStatus = FeedWaiting;
        userRequest(RequestTypeFeed);
        break;
    default:
        canvas_clear(canvas);
        canvas_set_font(canvas, FontPrimary);
        canvas_draw_str(canvas, 0, 10, "Loading feed...");
        break;
    }
}

void FlipSocialRun::drawLoginView(Canvas *canvas)
{
    canvas_clear(canvas);
    canvas_set_font(canvas, FontPrimary);
    static bool loadingStarted = false;
    switch (loginStatus)
    {
    case LoginWaiting:
        if (!loadingStarted)
        {
            if (!loading)
            {
                loading = std::make_unique<Loading>(canvas);
            }
            loadingStarted = true;
            if (loading)
            {
                loading->setText("Logging in...");
            }
        }
        if (!this->httpRequestIsFinished())
        {
            if (loading)
            {
                loading->animate(false);
            }
            else
            {
                loading = std::make_unique<Loading>(canvas);
            }
            if (http)
            {
                http->update(); // poll async
            }
        }
        else
        {
            printf("drawLoginView: HTTP request finished.\n");
            if (loading)
            {
                loading->stop();
            }
            loadingStarted = false;
            if (!http || http->getState() == ISSUE)
            {
                printf("drawLoginView: HTTP request failed or issue state\n");
                loginStatus = LoginRequestError;
                return;
            }
            std::string response = http->getAsyncResponse();
            if (!response.empty())
            {
                if (strstr(response.c_str(), "[SUCCESS]") != NULL)
                {
                    loginStatus = LoginSuccess;
                    currentView = SocialViewMenu;
                }
                else if (strstr(response.c_str(), "User not found") != NULL)
                {
                    loginStatus = LoginNotStarted;
                    currentView = SocialViewRegistration;
                    registrationStatus = RegistrationWaiting;
                    userRequest(RequestTypeRegistration);
                }
                else if (strstr(response.c_str(), "Incorrect password") != NULL)
                {
                    loginStatus = LoginWrongPassword;
                }
                else if (strstr(response.c_str(), "Username or password is empty.") != NULL)
                {
                    loginStatus = LoginCredentialsMissing;
                }
                else
                {
                    loginStatus = LoginRequestError;
                }
            }
            else
            {
                loginStatus = LoginRequestError;
            }
        }
        break;
    case LoginSuccess:
        canvas_draw_str(canvas, 0, 10, "Login successful!");
        canvas_draw_str(canvas, 0, 20, "Press OK to continue.");
        break;
    case LoginCredentialsMissing:
        canvas_draw_str(canvas, 0, 10, "Missing credentials!");
        canvas_draw_str(canvas, 0, 20, "Please set your username");
        canvas_draw_str(canvas, 0, 30, "and password in the app.");
        break;
    case LoginRequestError:
        canvas_draw_str(canvas, 0, 10, "Login request failed!");
        canvas_draw_str(canvas, 0, 20, "Check your network and");
        canvas_draw_str(canvas, 0, 30, "try again later.");
        break;
    case LoginWrongPassword:
        canvas_draw_str(canvas, 0, 10, "Wrong password!");
        canvas_draw_str(canvas, 0, 20, "Please check your password");
        canvas_draw_str(canvas, 0, 30, "and try again.");
        break;
    case LoginNotStarted:
        loginStatus = LoginWaiting;
        userRequest(RequestTypeLogin);
        break;
    default:
        canvas_draw_str(canvas, 0, 10, "Logging in...");
        break;
    }
}

void FlipSocialRun::drawMainMenuView(Canvas *canvas)
{
    const char *menuItems[] = {"Feed", "Post", "Messages", "Explore", "Profile"};
    drawMenu(canvas, (uint8_t)currentMenuIndex, menuItems, 5);
}

void FlipSocialRun::drawMenu(Canvas *canvas, uint8_t selectedIndex, const char **menuItems, uint8_t menuCount)
{
    // Clear canvas
    canvas_clear(canvas);

    // Target screen size for this layout
    const int SCREEN_W = 320;
    const int SCREEN_H = 320;

    // Draw title
    canvas_set_font_custom(canvas, FONT_SIZE_MEDIUM);
    const char *title = "FlipSocial";
    int title_width = canvas_string_width(canvas, title);
    int title_x = (SCREEN_W - title_width) / 2;
    canvas_draw_str(canvas, title_x + 15, 25, title);

    // Draw underline for title
    canvas_draw_line(canvas, title_x, 35, title_x + title_width, 35);

    // Draw decorative horizontal pattern
    for (int i = 0; i < SCREEN_W; i += 10)
    {
        canvas_draw_dot(canvas, i, 45);
    }

    // Menu items with word wrapping
    canvas_set_font_custom(canvas, FONT_SIZE_SMALL);
    const char *currentItem = menuItems[selectedIndex];

    const int box_padding = 25;
    const int box_width = 270;
    const int usable_width = box_width - (box_padding * 2); // text area inside box
    const int line_height = 20;
    const int max_lines = 2;

    int menu_y = 100;

    // Calculate word wrapping (character buffers stay same size)
    char lines[max_lines][64];
    int line_count = 0;

    const char *text = currentItem;
    int text_len = strlen(text);
    int current_pos = 0;

    while (current_pos < text_len && line_count < max_lines)
    {
        int line_start = current_pos;
        int last_space = -1;
        int current_width = 0;
        int char_pos = 0;

        // Find how much text fits on this line
        while (current_pos < text_len && char_pos < 63) // room for NUL
        {
            if (text[current_pos] == ' ')
            {
                last_space = char_pos;
            }

            lines[line_count][char_pos] = text[current_pos];
            char_pos++;

            // Temporary terminate and measure based on canvas font
            lines[line_count][char_pos] = '\0';
            current_width = canvas_string_width(canvas, lines[line_count]);

            if (current_width > usable_width)
            {
                // Text too wide, need to break
                if (last_space > 0)
                {
                    lines[line_count][last_space] = '\0';
                    current_pos = line_start + last_space + 1; // skip the space
                }
                else
                {
                    char_pos--;
                    lines[line_count][char_pos] = '\0';
                    current_pos = line_start + char_pos;
                }
                break;
            }

            current_pos++;
        }

        // If we've reached end of text
        if (current_pos >= text_len)
        {
            lines[line_count][char_pos] = '\0';
        }

        line_count++;
    }

    // Ellipsis if truncated
    if (current_pos < text_len && line_count == max_lines)
    {
        int last_line = line_count - 1;
        int line_len = strlen(lines[last_line]);
        if (line_len > 3)
        {
            strcpy(&lines[last_line][line_len - 3], "...");
        }
    }

    // Calculate box height and ensure a minimum
    int box_height = (line_count * line_height) + 20;
    if (box_height < 40)
        box_height = 40;

    int box_y_offset;
    if (line_count > 1)
    {
        box_y_offset = -55;
    }
    else
    {
        box_y_offset = -30;
    }

    // Draw main selection box (rounded)
    canvas_draw_rbox(canvas, 25, menu_y + box_y_offset, box_width, box_height, 10, TFT_BLACK);

    // Draw each line of text centered
    for (int i = 0; i < line_count; i++)
    {
        int line_width = canvas_string_width(canvas, lines[i]);
        int line_x = (SCREEN_W - line_width) / 2;
        int text_y_offset = (line_count > 1) ? -45 : -20;
        int line_y = menu_y + (i * line_height) + 10 + text_y_offset;
        canvas_draw_str(canvas, line_x, line_y, lines[i], TFT_WHITE);
    }

    // Draw navigation arrows
    if (selectedIndex > 0)
    {
        canvas_draw_str(canvas, 5, menu_y - 7, "<", TFT_BLACK);
    }
    if (selectedIndex < (menuCount - 1))
    {
        canvas_draw_str(canvas, SCREEN_W - 15, menu_y - 7, ">", TFT_BLACK);
    }

    const int MAX_DOTS = 15;
    const int dots_spacing = 15;
    int indicator_y = 130;

    if (menuCount <= MAX_DOTS)
    {
        // Show all dots if they fit
        int dots_start_x = (SCREEN_W - (menuCount * dots_spacing)) / 2;
        for (int i = 0; i < menuCount; i++)
        {
            int dot_x = dots_start_x + (i * dots_spacing);
            if (i == selectedIndex)
            {
                canvas_draw_box(canvas, dot_x, indicator_y, 10, 10, TFT_BLACK);
            }
            else
            {
                canvas_draw_frame(canvas, dot_x, indicator_y, 10, 10, TFT_BLACK);
            }
        }
    }
    else
    {
        // condensed indicator with current position
        canvas_set_font_custom(canvas, FONT_SIZE_SMALL);
        char position_text[16];
        snprintf(position_text, sizeof(position_text), "%d/%d", selectedIndex + 1, menuCount);
        int pos_width = canvas_string_width(canvas, position_text);
        int pos_x = (SCREEN_W - pos_width) / 2;
        canvas_draw_str(canvas, pos_x, indicator_y + 8, position_text, TFT_BLACK);

        // progress bar
        int bar_width = 150;
        int bar_x = (SCREEN_W - bar_width) / 2;
        int bar_y = indicator_y - 15;
        canvas_draw_frame(canvas, bar_x, bar_y, bar_width, 8, TFT_BLACK);
        int progress_width = 0;
        if (menuCount > 1)
        {
            progress_width = (selectedIndex * (bar_width - 2)) / (menuCount - 1);
            if (progress_width < 0)
                progress_width = 0;
        }
        else
        {
            progress_width = bar_width - 2;
        }
        canvas_draw_box(canvas, bar_x + 1, bar_y + 1, progress_width, 6, TFT_BLACK);
    }

    // Draw decorative bottom pattern
    for (int i = 0; i < SCREEN_W; i += 10)
    {
        canvas_draw_dot(canvas, i, 145, TFT_BLACK);
    }

    canvas_set_font_custom(canvas, FONT_SIZE_MEDIUM);
}

void FlipSocialRun::drawMessagesView(Canvas *canvas)
{
    canvas_clear(canvas);
    canvas_set_font(canvas, FontPrimary);
    static bool loadingStarted = false;
    switch (messagesStatus)
    {
    case MessagesWaiting:
        if (!loadingStarted)
        {
            if (!loading)
            {
                loading = std::make_unique<Loading>(canvas);
            }
            loadingStarted = true;
            if (loading)
            {
                loading->setText("Retrieving...");
            }
        }
        if (!this->httpRequestIsFinished())
        {
            if (loading)
            {
                loading->animate(false);
            }
            else
            {
                loading = std::make_unique<Loading>(canvas);
            }
            if (http)
            {
                http->update(); // poll async
            }
        }
        else
        {
            if (loading)
            {
                loading->stop();
            }
            loadingStarted = false;
            if (!http || http->getState() == ISSUE)
            {
                messagesStatus = MessagesRequestError;
                return;
            }
            if (strstr(http->getAsyncResponse().c_str(), "conversations") != NULL)
            {
                messagesStatus = MessagesSuccess;
                return;
            }
            else
            {
                messagesStatus = MessagesRequestError;
            }
        }
        break;
    case MessagesSuccess:
    {
        if (!http)
        {
            printf("drawMessageUsersView: Failed to load messages user list from storage\n");
            canvas_draw_str(canvas, 0, 30, "Failed to load messages.");
            return;
        }

        // Target screen size for this layout
        const int SCREEN_W = 320;
        const int SCREEN_H = 320;

        // draw the current message
        for (int i = 0; i < MAX_MESSAGES; i++)
        {
            if (i != messagesIndex)
            {
                continue; // only draw the current displayed message
            }
            auto response = http->getAsyncResponse();
            std::string message = getJsonArrayValue(response.c_str(), "conversations", i);
            if (message.empty())
            {
                printf("drawMessagesView: Failed to get message from JSON\n");
                if (messagesIndex > 0)
                {
                    // go back to the previous message if current is not found
                    messagesIndex--;
                }
                return;
            }

            std::string sender = getJsonValue(message.c_str(), "sender");
            std::string content = getJsonValue(message.c_str(), "content");
            if (sender.empty() || content.empty())
            {
                printf("drawMessagesView: Failed to parse message data\n");
                return;
            }

            // Draw title (sender name)
            canvas_set_font_custom(canvas, FONT_SIZE_MEDIUM);
            int title_width = canvas_string_width(canvas, sender.c_str());
            int title_x = (SCREEN_W - title_width) / 2;
            canvas_draw_str(canvas, title_x + 15, 25, sender.c_str());

            // Draw underline for title
            canvas_draw_line(canvas, title_x, 35, title_x + title_width, 35);

            // Draw decorative horizontal pattern
            for (int i = 0; i < SCREEN_W; i += 10)
            {
                canvas_draw_dot(canvas, i, 45);
            }

            // Message content with word wrapping
            canvas_set_font_custom(canvas, FONT_SIZE_SMALL);

            const int box_padding = 25;
            const int box_width = 270;
            const int line_height = 20;

            int menu_y = 100;

            // Calculate box height based on content lines
            int content_lines = 1;
            if (content.length() > 30)
                content_lines = 2;
            if (content.length() > 60)
                content_lines = 3;

            int box_height = (content_lines * line_height) + 20;
            if (box_height < 40)
                box_height = 40;

            int box_y_offset = (content_lines > 1) ? -45 : -30;

            // Draw main content box (rounded)
            canvas_draw_rbox(canvas, 25, menu_y + box_y_offset, box_width, box_height, 10, TFT_BLACK);

            // Draw message content centered in white
            canvas_set_color(canvas, ColorWhite);

            // Simple word wrapping for message content
            if (content.length() <= 30)
            {
                // Single line
                int line_width = canvas_string_width(canvas, content.c_str());
                int line_x = (SCREEN_W - line_width) / 2;
                int line_y = menu_y + 10 - 20;
                canvas_draw_str(canvas, line_x, line_y, content.c_str(), TFT_WHITE);
            }
            else
            {
                // Multi-line - break at word boundaries
                std::string line1, line2;
                size_t break_pos = content.find_last_of(' ', 30);
                if (break_pos != std::string::npos && break_pos > 15)
                {
                    line1 = content.substr(0, break_pos);
                    line2 = content.substr(break_pos + 1);
                    if (line2.length() > 30)
                    {
                        line2 = line2.substr(0, 27) + "...";
                    }
                }
                else
                {
                    line1 = content.substr(0, 30);
                    line2 = content.length() > 30 ? content.substr(30, 27) + "..." : "";
                }

                // Draw first line
                int line1_width = canvas_string_width(canvas, line1.c_str());
                int line1_x = (SCREEN_W - line1_width) / 2;
                int line1_y = menu_y + 10 - 30;
                canvas_draw_str(canvas, line1_x, line1_y, line1.c_str(), TFT_WHITE);

                // Draw second line if it exists
                if (!line2.empty())
                {
                    int line2_width = canvas_string_width(canvas, line2.c_str());
                    int line2_x = (SCREEN_W - line2_width) / 2;
                    int line2_y = menu_y + 10 - 10;
                    canvas_draw_str(canvas, line2_x, line2_y, line2.c_str(), TFT_WHITE);
                }
            }

            canvas_set_color(canvas, ColorBlack);

            // Draw navigation arrows
            if (messagesIndex > 0)
            {
                canvas_draw_str(canvas, 5, menu_y - 7, "<", TFT_BLACK);
            }

            // Check if there's a next message available
            std::string nextMessage = getJsonArrayValue(response.c_str(), "conversations", messagesIndex + 1);
            if (messagesIndex < (MAX_MESSAGES - 1) && !nextMessage.empty())
            {
                canvas_draw_str(canvas, SCREEN_W - 15, menu_y - 7, ">", TFT_BLACK);
            }

            // Draw message counter and reply indicator
            int indicator_y = 130;

            // Message counter
            char message_counter[32];
            int total_messages = 0;
            // Count total messages
            for (int j = 0; j < MAX_MESSAGES; j++)
            {
                std::string tempMessage = getJsonArrayValue(response.c_str(), "conversations", j);
                if (!tempMessage.empty())
                {
                    total_messages++;
                }
                else
                {
                    break;
                }
            }
            snprintf(message_counter, sizeof(message_counter), "%d/%d", messagesIndex + 1, total_messages);
            int counter_width = canvas_string_width(canvas, message_counter);
            int counter_x = (SCREEN_W - counter_width) / 2;
            canvas_draw_str(canvas, counter_x, indicator_y, message_counter, TFT_BLACK);

            // Reply indicator
            const char *reply_text = "Press OK to Reply";
            int reply_width = canvas_string_width(canvas, reply_text);
            int reply_x = (SCREEN_W - reply_width) / 2;
            canvas_draw_str(canvas, reply_x, indicator_y + 15, reply_text, TFT_BLACK);

            // Draw decorative bottom pattern
            for (int i = 0; i < SCREEN_W; i += 10)
            {
                canvas_draw_dot(canvas, i, 145, TFT_BLACK);
            }

            canvas_set_font_custom(canvas, FONT_SIZE_MEDIUM);
        }
        break;
    }
    case MessagesRequestError:
        canvas_draw_str(canvas, 0, 10, "Messages request failed!");
        canvas_draw_str(canvas, 0, 20, "Check your network and");
        canvas_draw_str(canvas, 0, 30, "try again later.");
        break;
    case MessagesParseError:
        canvas_draw_str(canvas, 0, 10, "Error parsing messages!");
        canvas_draw_str(canvas, 0, 20, "Please set your username");
        canvas_draw_str(canvas, 0, 30, "and password in the app.");
        break;
    case MessagesNotStarted:
        messagesStatus = MessagesWaiting;
        userRequest(RequestTypeMessagesWithUser);
        break;
    case MessagesKeyboard:
    {
        auto keyboard = viewManager->getKeyboard();
        if (keyboard)
        {
            keyboard->run(false);
        }
        break;
    }
    case MessagesSending:
        if (!loadingStarted)
        {
            if (!loading)
            {
                loading = std::make_unique<Loading>(canvas);
            }
            loadingStarted = true;
            if (loading)
            {
                loading->setText("Sending...");
            }
        }
        if (!this->httpRequestIsFinished())
        {
            if (loading)
            {
                loading->animate(false);
            }
            else
            {
                loading = std::make_unique<Loading>(canvas);
            }
            if (http)
            {
                http->update(); // poll async
            }
        }
        else
        {
            if (loading)
            {
                loading->stop();
            }
            loadingStarted = false;
            if (!http || http->getState() == ISSUE)
            {
                messagesStatus = MessagesRequestError;
                return;
            }
            if (strstr(http->getAsyncResponse().c_str(), "[SUCCESS]") != NULL)
            {
                messagesStatus = MessagesNotStarted;
                messagesIndex = 0;
                return;
            }
            else
            {
                messagesStatus = MessagesRequestError;
            }
        }
        break;
    default:
        canvas_draw_str(canvas, 0, 10, "Retrieving messages...");
        break;
    }
}

void FlipSocialRun::drawMessageUsersView(Canvas *canvas)
{
    canvas_clear(canvas);
    canvas_set_font(canvas, FontPrimary);
    static bool loadingStarted = false;
    switch (messageUsersStatus)
    {
    case MessageUsersWaiting:
        if (!loadingStarted)
        {
            if (!loading)
            {
                loading = std::make_unique<Loading>(canvas);
            }
            loadingStarted = true;
            if (loading)
            {
                loading->setText("Retrieving...");
            }
        }
        if (!this->httpRequestIsFinished())
        {
            if (loading)
            {
                loading->animate(false);
            }
            else
            {
                loading = std::make_unique<Loading>(canvas);
            }
            if (http)
            {
                http->update(); // poll async
            }
        }
        else
        {
            if (loading)
            {
                loading->stop();
            }
            loadingStarted = false;
            if (!http || http->getState() == ISSUE)
            {
                messageUsersStatus = MessageUsersRequestError;
                return;
            }
            auto response = http->getAsyncResponse();
            if (strstr(response.c_str(), "users") != NULL)
            {
                messageUsersStatus = MessageUsersSuccess;
                // we should save the response
                auto storage = viewManager->getStorage();
                if (!storage.write(FLIP_SOCIAL_MESSAGE_USER_LIST_PATH, response.c_str(), response.size()))
                {
                    printf("Failed to save message user list to storage.\n");
                }
                return;
            }
            else
            {
                messageUsersStatus = MessageUsersRequestError;
            }
        }
        break;
    case MessageUsersSuccess:
    {
        canvas_draw_str(canvas, 0, 10, "Messages retrieved successfully!");
        canvas_draw_str(canvas, 0, 20, "Press OK to continue.");

        if (!http)
        {
            printf("drawMessageUsersView: Failed to load messages user list from storage\n");
            canvas_draw_str(canvas, 0, 30, "Failed to load messages.");
            return;
        }

        char *userList = (char *)malloc(1024);
        if (!userList)
        {
            printf("Failed to allocate memory for user list.\n");
            canvas_draw_str(canvas, 0, 30, "Failed to allocate memory.");
            return;
        }

        auto storage = viewManager->getStorage();
        size_t bytes_read = 0;
        if (!storage.read(FLIP_SOCIAL_MESSAGE_USER_LIST_PATH, userList, 1024, &bytes_read))
        {
            printf("Failed to read message user list from storage.\n");
            canvas_draw_str(canvas, 0, 30, "Failed to load messages.");
            free(userList);
            return;
        }
        userList[bytes_read] = '\0'; // Ensure null termination at actual read length

        // store users
        std::vector<std::string> usersList;
        for (int i = 0; i < MAX_MESSAGE_USERS; i++)
        {
            std::string user = getJsonArrayValue(userList, "users", i);
            if (user.empty())
            {
                break; // No more users in the list
            }
            usersList.push_back(user);
        }

        if (usersList.empty())
        {
            canvas_draw_str(canvas, 0, 30, "No messages found.");
        }
        else
        {
            // std::vector<std::string> to const char** for drawMenu
            std::vector<const char *> userPtrs;
            userPtrs.reserve(usersList.size());
            for (const auto &user : usersList)
            {
                userPtrs.push_back(user.c_str());
            }
            drawMenu(canvas, messageUserIndex, userPtrs.data(), userPtrs.size());
        }
        free(userList);
        break;
    }
    case MessageUsersRequestError:
        canvas_draw_str(canvas, 0, 10, "Messages request failed!");
        canvas_draw_str(canvas, 0, 20, "Check your network and");
        canvas_draw_str(canvas, 0, 30, "try again later.");
        break;
    case MessageUsersParseError:
        canvas_draw_str(canvas, 0, 10, "Error parsing messages!");
        canvas_draw_str(canvas, 0, 20, "Please set your username");
        canvas_draw_str(canvas, 0, 30, "and password in the app.");
        break;
    case MessageUsersNotStarted:
        messageUsersStatus = MessageUsersWaiting;
        userRequest(RequestTypeMessagesUserList);
        break;
    default:
        canvas_draw_str(canvas, 0, 10, "Retrieving messages...");
        break;
    }
}

void FlipSocialRun::drawPostView(Canvas *canvas)
{
    canvas_clear(canvas);
    canvas_set_font(canvas, FontPrimary);
    static bool loadingStarted = false;
    switch (postStatus)
    {
    case PostWaiting:
        if (!loadingStarted)
        {
            if (!loading)
            {
                loading = std::make_unique<Loading>(canvas);
            }
            loadingStarted = true;
            if (loading)
            {
                loading->setText("Posting...");
            }
        }
        if (!this->httpRequestIsFinished())
        {
            if (loading)
            {
                loading->animate(false);
            }
            else
            {
                loading = std::make_unique<Loading>(canvas);
            }
            if (http)
            {
                http->update(); // poll async
            }
        }
        else
        {
            if (loading)
            {
                loading->stop();
            }
            loadingStarted = false;
            if (!http || http->getState() == ISSUE)
            {
                postStatus = PostRequestError;
                return;
            }
            if (http->getAsyncResponse().find("[SUCCESS]") != std::string::npos)
            {
                postStatus = PostSuccess;
                currentView = SocialViewFeed;
                currentMenuIndex = SocialViewFeed;
                feedStatus = FeedNotStarted;
                feedIteration = 1;
                feedItemIndex = 0;
                return;
            }
            else
            {
                postStatus = PostRequestError;
            }
        }
        break;
    case PostSuccess:
        // unlike other "views", we shouldnt hit here
        // since after posting, users will be redirected to feed
        canvas_draw_str(canvas, 0, 10, "Posted successfully!");
        canvas_draw_str(canvas, 0, 20, "Press OK to continue.");
        break;
    case PostRequestError:
        canvas_draw_str(canvas, 0, 10, "Post request failed!");
        canvas_draw_str(canvas, 0, 20, "Ensure your message");
        canvas_draw_str(canvas, 0, 30, "follows the rules.");
        break;
    case PostParseError:
        canvas_draw_str(canvas, 0, 10, "Error parsing post!");
        canvas_draw_str(canvas, 0, 20, "Ensure your message");
        canvas_draw_str(canvas, 0, 30, "follows the rules.");
        break;
    case PostKeyboard:
    {
        auto keyboard = viewManager->getKeyboard();
        if (keyboard)
        {
            keyboard->run(false);
        }
        break;
    }
    case PostChoose:
    {
        char *preSavedMessages = (char *)malloc(1024);
        if (!preSavedMessages)
        {
            printf("drawPostView: Failed to allocate memory for preSavedMessages.\n");
            postStatus = PostParseError;
            return;
        }
        bool exists = false;
        auto storage = viewManager->getStorage();
        size_t bytes_read = 0;
        if (!storage.read(FLIP_SOCIAL_PRESAVES_PATH, preSavedMessages, 1024, &bytes_read))
        {
            //  create the file here if not loaded
            if (!storage.createFile(FLIP_SOCIAL_PRESAVES_PATH))
            {
                printf("Failed to load and create pre-saved messages.\n");
                canvas_draw_str(canvas, 0, 10, "Failed to load and create pre-saved messages.");
                free(preSavedMessages);
                return;
            }
        }
        preSavedMessages[bytes_read] = '\0'; // Ensure null termination at actual read length

        // Parse pre-saved messages (each line is a message)
        std::vector<std::string> preSavedList;
        char *start = preSavedMessages;
        char *end = preSavedMessages;
        int preSavedCount = 0;
        while (*end != '\0' && preSavedCount < MAX_PRE_SAVED_MESSAGES)
        {
            if (*end == '\n')
            {
                if (end > start)
                {
                    preSavedList.push_back(std::string(start, end - start));
                    preSavedCount++;
                }
                end++;
                start = end;
            }
            else
            {
                end++;
            }
        }
        // Add the last line if not empty and not ending with a newline, and if limit not reached
        if (end > start && preSavedCount < MAX_PRE_SAVED_MESSAGES)
        {
            preSavedList.push_back(std::string(start, end - start));
        }

        // Insert "[New Post]" as the first item, then add user's pre-saved messages
        std::vector<std::string> menuItems;
        menuItems.push_back("[New Post]");
        for (const auto &msg : preSavedList)
        {
            menuItems.push_back(msg);
        }

        // Convert std::vector<std::string> to const char** for drawMenu
        std::vector<const char *> preSavedPtrs;
        preSavedPtrs.reserve(menuItems.size());
        for (const auto &msg : menuItems)
        {
            preSavedPtrs.push_back(msg.c_str());
        }

        // Draw the menu with [New Post] and pre-saved messages
        drawMenu(canvas, postIndex, preSavedPtrs.data(), preSavedPtrs.size());

        free(preSavedMessages);
        break;
    }
    default:
        canvas_draw_str(canvas, 0, 10, "Awaiting...");
        break;
    }
}

void FlipSocialRun::drawProfileView(Canvas *canvas)
{
    canvas_clear(canvas);

    // Target screen size for this layout
    const int SCREEN_W = 320;
    const int SCREEN_H = 320;

    char userInfo[256];
    auto storage = viewManager->getStorage();
    size_t bytes_read = 0;
    if (!storage.read(FLIP_SOCIAL_PROFILE_PATH, userInfo, sizeof(userInfo), &bytes_read))
    {
        printf("Failed to load profile data.\n");
        canvas_set_font(canvas, FontSecondary);
        canvas_draw_str_aligned(canvas, SCREEN_W / 2, 80, AlignCenter, AlignCenter,
                                "Failed to load user info.");
        return;
    }
    userInfo[bytes_read] = '\0'; // Ensure null termination at actual read length

    std::string username = flipSocialUtilsLoadUserFromFlash(viewManager);
    if (username.empty())
    {
        canvas_set_font(canvas, FontSecondary);
        canvas_draw_str_aligned(canvas, SCREEN_W / 2, 80, AlignCenter, AlignCenter,
                                "Failed to load username.");
        return;
    }

    std::string bio = getJsonValue(userInfo, "bio");
    std::string friendsCount = getJsonValue(userInfo, "friends_count");
    std::string dateCreated = getJsonValue(userInfo, "date_created");

    if (bio.empty() || friendsCount.empty() || dateCreated.empty())
    {
        canvas_set_font(canvas, FontSecondary);
        canvas_draw_str_aligned(canvas, SCREEN_W / 2, 80, AlignCenter, AlignCenter,
                                "Incomplete profile data.");
        return;
    }

    // Draw title
    canvas_set_font_custom(canvas, FONT_SIZE_MEDIUM);
    int title_width = canvas_string_width(canvas, username.c_str());
    int title_x = (SCREEN_W - title_width) / 2;
    canvas_draw_str(canvas, title_x + 15, 25, username.c_str());

    // Draw underline for title
    canvas_draw_line(canvas, title_x, 35, title_x + title_width, 35);

    // Draw decorative horizontal pattern
    for (int i = 0; i < SCREEN_W; i += 10)
    {
        canvas_draw_dot(canvas, i, 45);
    }

    // Profile element labels
    const char *elementLabels[] = {"Bio", "Friends", "Joined"};

    // Menu items with word wrapping
    canvas_set_font_custom(canvas, FONT_SIZE_SMALL);
    const char *currentLabel = elementLabels[currentProfileElement];

    const int box_padding = 25;
    const int box_width = 270;
    const int line_height = 20;
    const int max_lines = 2;

    int menu_y = 100;

    // Calculate box height and ensure a minimum
    int box_height = 40; // minimum height for profile content

    int box_y_offset = -30; // single line offset

    // Draw main selection box (rounded)
    canvas_draw_rbox(canvas, 25, menu_y + box_y_offset, box_width, box_height, 10, TFT_BLACK);

    // Draw content based on current element
    canvas_set_color(canvas, ColorWhite);
    switch (currentProfileElement)
    {
    case ProfileElementBio:
        if (bio.empty())
        {
            int line_width = canvas_string_width(canvas, "No bio");
            int line_x = (SCREEN_W - line_width) / 2;
            int line_y = menu_y + 10 - 20;
            canvas_draw_str(canvas, line_x, line_y, "No bio", TFT_WHITE);
        }
        else
        {
            // Center the bio text
            int line_width = canvas_string_width(canvas, bio.c_str());
            int line_x = (SCREEN_W - line_width) / 2;
            int line_y = menu_y + 10 - 20;
            canvas_draw_str(canvas, line_x, line_y, bio.c_str(), TFT_WHITE);
        }
        break;
    case ProfileElementFriends:
    {
        int line_width = canvas_string_width(canvas, friendsCount.c_str());
        int line_x = (SCREEN_W - line_width) / 2;
        int line_y = menu_y + 10 - 20;
        canvas_draw_str(canvas, line_x, line_y, friendsCount.c_str(), TFT_WHITE);
    }
    break;
    case ProfileElementJoined:
    {
        int line_width = canvas_string_width(canvas, dateCreated.c_str());
        int line_x = (SCREEN_W - line_width) / 2;
        int line_y = menu_y + 10 - 20;
        canvas_draw_str(canvas, line_x, line_y, dateCreated.c_str(), TFT_WHITE);
    }
    break;
    default:
        int line_width = canvas_string_width(canvas, "Unknown");
        int line_x = (SCREEN_W - line_width) / 2;
        int line_y = menu_y + 10 - 20;
        canvas_draw_str(canvas, line_x, line_y, "Unknown", TFT_WHITE);
        break;
    }

    canvas_set_color(canvas, ColorBlack);

    // Draw navigation arrows
    if (currentProfileElement > 0)
    {
        canvas_draw_str(canvas, 5, menu_y - 7, "<", TFT_BLACK);
    }
    if (currentProfileElement < (ProfileElementMAX - 1))
    {
        canvas_draw_str(canvas, SCREEN_W - 15, menu_y - 7, ">", TFT_BLACK);
    }

    const int MAX_DOTS = 15;
    const int dots_spacing = 15;
    int indicator_y = 130;

    if (ProfileElementMAX <= MAX_DOTS)
    {
        // Show all dots if they fit
        int dots_start_x = (SCREEN_W - (ProfileElementMAX * dots_spacing)) / 2;
        for (int i = 0; i < ProfileElementMAX; i++)
        {
            int dot_x = dots_start_x + (i * dots_spacing);
            if (i == currentProfileElement)
            {
                canvas_draw_box(canvas, dot_x, indicator_y, 8, 8, TFT_BLACK);
            }
            else
            {
                canvas_draw_frame(canvas, dot_x, indicator_y, 8, 8, TFT_BLACK);
            }
        }
    }

    // Draw decorative bottom pattern
    for (int i = 0; i < SCREEN_W; i += 10)
    {
        canvas_draw_dot(canvas, i, 145, TFT_BLACK);
    }

    canvas_set_font_custom(canvas, FONT_SIZE_MEDIUM);
}

void FlipSocialRun::drawWrappedBio(Canvas *canvas, const char *text, uint8_t x, uint8_t y)
{
    if (!text || strlen(text) == 0)
    {
        canvas_draw_str_aligned(canvas, 64, y + 2, AlignCenter, AlignCenter, "No bio");
        return;
    }

    const uint8_t maxCharsPerLine = 18;
    uint8_t textLen = strlen(text);

    if (textLen <= maxCharsPerLine)
    {
        canvas_draw_str_aligned(canvas, 64, y + 2, AlignCenter, AlignCenter, text);
        return;
    }

    char line1[maxCharsPerLine + 1] = {0};
    char line2[maxCharsPerLine + 1] = {0};

    // First line
    uint8_t line1Len = (textLen > maxCharsPerLine) ? maxCharsPerLine : textLen;

    // Try to break at word boundary for first line
    uint8_t breakPoint = line1Len;
    if (textLen > maxCharsPerLine)
    {
        for (int i = maxCharsPerLine - 1; i > maxCharsPerLine - 8; i--) // Look back up to 7 chars
        {
            if (text[i] == ' ')
            {
                breakPoint = i;
                break;
            }
        }
    }

    strncpy(line1, text, breakPoint);
    line1[breakPoint] = '\0';

    // Second line
    if (textLen > breakPoint)
    {
        uint8_t remainingLen = textLen - breakPoint;
        if (text[breakPoint] == ' ')
            breakPoint++; // Skip space at beginning of line2

        uint8_t line2Len = (remainingLen > maxCharsPerLine) ? maxCharsPerLine - 3 : remainingLen;
        strncpy(line2, &text[breakPoint], line2Len);

        // Add ellipsis if text is truncated
        if (remainingLen > maxCharsPerLine)
        {
            line2[line2Len - 3] = '.';
            line2[line2Len - 2] = '.';
            line2[line2Len - 1] = '.';
        }
        line2[line2Len] = '\0';
    }

    // Draw the lines
    canvas_draw_str(canvas, x, y, line1);
    if (strlen(line2) > 0)
    {
        canvas_draw_str(canvas, x, y + 8, line2);
    }
}

void FlipSocialRun::drawRegistrationView(Canvas *canvas)
{
    canvas_clear(canvas);
    canvas_set_font(canvas, FontPrimary);
    static bool loadingStarted = false;
    switch (registrationStatus)
    {
    case RegistrationWaiting:
        if (!loadingStarted)
        {
            if (!loading)
            {
                loading = std::make_unique<Loading>(canvas);
            }
            loadingStarted = true;
            if (loading)
            {
                loading->setText("Registering...");
            }
        }
        if (!this->httpRequestIsFinished())
        {
            if (loading)
            {
                loading->animate(false);
            }
            else
            {
                loading = std::make_unique<Loading>(canvas);
            }
            if (http)
            {
                http->update(); // poll async
            }
        }
        else
        {
            if (loading)
            {
                loading->stop();
            }
            loadingStarted = false;
            if (!http || http->getState() == ISSUE)
            {
                registrationStatus = RegistrationRequestError;
                return;
            }
            std::string response = http->getAsyncResponse();
            if (!response.empty())
            {
                if (strstr(response.c_str(), "[SUCCESS]") != NULL)
                {
                    registrationStatus = RegistrationSuccess;
                    currentView = SocialViewMenu;
                }
                else if (strstr(response.c_str(), "Username or password not provided") != NULL)
                {
                    registrationStatus = RegistrationCredentialsMissing;
                }
                else if (strstr(response.c_str(), "User already exists") != NULL)
                {
                    registrationStatus = RegistrationUserExists;
                }
                else
                {
                    registrationStatus = RegistrationRequestError;
                }
            }
            else
            {
                registrationStatus = RegistrationRequestError;
            }
        }
        break;
    case RegistrationSuccess:
        canvas_draw_str(canvas, 0, 10, "Registration successful!");
        canvas_draw_str(canvas, 0, 20, "Press OK to continue.");
        break;
    case RegistrationCredentialsMissing:
        canvas_draw_str(canvas, 0, 10, "Missing credentials!");
        canvas_draw_str(canvas, 0, 20, "Please set your username");
        canvas_draw_str(canvas, 0, 30, "and password in the app.");
        break;
    case RegistrationRequestError:
        canvas_draw_str(canvas, 0, 10, "Registration request failed!");
        canvas_draw_str(canvas, 0, 20, "Check your network and");
        canvas_draw_str(canvas, 0, 30, "try again later.");
        break;
    default:
        canvas_draw_str(canvas, 0, 10, "Registering...");
        break;
    }
}

void FlipSocialRun::drawUserInfoView(Canvas *canvas)
{
    static bool loadingStarted = false;
    switch (userInfoStatus)
    {
    case UserInfoWaiting:
        if (!loadingStarted)
        {
            if (!loading)
            {
                loading = std::make_unique<Loading>(canvas);
            }
            loadingStarted = true;
            if (loading)
            {
                loading->setText("Syncing...");
            }
        }
        if (!this->httpRequestIsFinished())
        {
            if (loading)
            {
                loading->animate(false);
            }
            else
            {
                loading = std::make_unique<Loading>(canvas);
            }
            if (http)
            {
                http->update(); // poll async
            }
        }
        else
        {
            canvas_draw_str(canvas, 0, 10, "Loading user info...");
            canvas_draw_str(canvas, 0, 20, "Please wait...");
            canvas_draw_str(canvas, 0, 30, "It may take up to 15 seconds.");
            if (!http || http->getState() == ISSUE)
            {
                userInfoStatus = UserInfoRequestError;
                if (loading)
                {
                    loading->stop();
                }
                loadingStarted = false;
                return;
            }
            if (!http->getAsyncResponse().empty())
            {
                userInfoStatus = UserInfoSuccess;

                // save login status
                auto storage = viewManager->getStorage();
                std::string success = "success";
                if (!storage.write(FLIP_SOCIAL_LOGIN_PATH, success.c_str(), success.size()))
                {
                    printf("Failed to save user's login status.\n");
                    userInfoStatus = UserInfoParseError;
                }

                // save user info
                auto response = http->getAsyncResponse();
                if (!storage.write(FLIP_SOCIAL_PROFILE_PATH, response.c_str(), response.size()))
                {
                    printf("Failed to save user's profile data.\n");
                    userInfoStatus = UserInfoParseError;
                }

                if (loading)
                {
                    loading->stop();
                }
                loadingStarted = false;
                currentView = SocialViewProfile;
                return;
            }
            else
            {
                userInfoStatus = UserInfoRequestError;
            }
        }
        break;
    case UserInfoSuccess:
        canvas_clear(canvas);
        canvas_set_font(canvas, FontPrimary);
        canvas_draw_str(canvas, 0, 10, "User info loaded successfully!");
        canvas_draw_str(canvas, 0, 20, "Press OK to continue.");
        break;
    case UserInfoCredentialsMissing:
        canvas_clear(canvas);
        canvas_set_font(canvas, FontPrimary);
        canvas_draw_str(canvas, 0, 10, "Missing credentials!");
        canvas_draw_str(canvas, 0, 20, "Please update your username");
        canvas_draw_str(canvas, 0, 30, "and password in the settings.");
        break;
    case UserInfoRequestError:
        canvas_clear(canvas);
        canvas_set_font(canvas, FontPrimary);
        canvas_draw_str(canvas, 0, 10, "User info request failed!");
        canvas_draw_str(canvas, 0, 20, "Check your network and");
        canvas_draw_str(canvas, 0, 30, "try again later.");
        break;
    case UserInfoParseError:
        canvas_clear(canvas);
        canvas_set_font(canvas, FontPrimary);
        canvas_draw_str(canvas, 0, 10, "Failed to parse user info!");
        canvas_draw_str(canvas, 0, 20, "Try again...");
        break;
    default:
        canvas_clear(canvas);
        canvas_set_font(canvas, FontPrimary);
        canvas_draw_str(canvas, 0, 10, "Loading user info...");
        break;
    }
}

bool FlipSocialRun::getMessageUser(char *buffer, size_t buffer_size)
{
    char *messagesUserList = (char *)malloc(1024);
    if (!messagesUserList)
    {
        printf("getMessageUser: Failed to allocate memory for messagesUserList.\n");
        return false;
    }
    auto storage = viewManager->getStorage();
    size_t bytes_read = 0;
    if (!storage.read(currentMenuIndex == SocialViewExplore ? FLIP_SOCIAL_EXPLORE_LIST_PATH : FLIP_SOCIAL_MESSAGE_USER_LIST_PATH, messagesUserList, 1024, &bytes_read))
    {
        printf("Failed to load messages user list from storage.\n");
        free(messagesUserList);
        return false;
    }
    messagesUserList[bytes_read] = '\0'; // Ensure null termination at actual read length
    uint8_t index = currentMenuIndex == SocialViewExplore ? exploreIndex : messageUserIndex;
    for (int i = 0; i < MAX_MESSAGE_USERS; i++)
    {
        if (i != index)
        {
            continue; // Only return the requested user
        }
        std::string user = getJsonArrayValue(messagesUserList, "users", i);
        if (!user.empty())
        {
            snprintf(buffer, buffer_size, "%s", user.c_str());
            free(messagesUserList);
            return true;
        }
    }
    free(messagesUserList);
    return false;
}

bool FlipSocialRun::getSelectedPost(char *buffer, size_t buffer_size)
{
    if (postIndex == 0)
    {
        // If postIndex is 0, we are in the "New Post" mode
        snprintf(buffer, buffer_size, "[New Post]");
        return true;
    }
    char *preSavedMessages = (char *)malloc(1024);
    if (!preSavedMessages)
    {
        printf("getSelectedPost: Failed to allocate memory for preSavedMessages\n");
        return false;
    }

    auto storage = viewManager->getStorage();
    size_t bytes_read = 0;
    if (!storage.read(FLIP_SOCIAL_PRESAVES_PATH, preSavedMessages, 1024, &bytes_read))
    {
        printf("Failed to load pre-saved messages.\n");
        free(preSavedMessages);
        return false;
    }
    preSavedMessages[bytes_read] = '\0'; // Ensure null termination at actual read length

    // grab only the selected post
    char *start = preSavedMessages;
    char *end = preSavedMessages;
    int postCount = 0;
    while (*end != '\0')
    {
        if (*end == '\n')
        {
            if (postCount == postIndex - 1)
            {
                // Found the selected post
                size_t length = end - start;
                if (length < buffer_size)
                {
                    snprintf(buffer, buffer_size, "%.*s", (int)length, start);
                    free(preSavedMessages);
                    return true;
                }
                else
                {
                    printf("getSelectedPost: Buffer size is too small for the post.\n");
                    free(preSavedMessages);
                    return false;
                }
            }
            postCount++;
            start = end + 1; // Move to the next line
        }
        end++;
    }

    free(preSavedMessages);
    return false; // Post not found
}

bool FlipSocialRun::httpRequestIsFinished()
{
    if (!http)
    {
        printf("httpRequestIsFinished: HTTP context is NULL\n");
        return true;
    }
    auto state = http->getState();
    return state == IDLE || state == ISSUE;
}

void FlipSocialRun::updateDraw(Canvas *canvas)
{
    canvas_clear(canvas);
    switch (currentView)
    {
    case SocialViewMenu:
        drawMainMenuView(canvas);
        break;
    case SocialViewLogin:
        drawLoginView(canvas);
        break;
    case SocialViewRegistration:
        drawRegistrationView(canvas);
        break;
    case SocialViewUserInfo:
        drawUserInfoView(canvas);
        break;
    case SocialViewProfile:
        drawProfileView(canvas);
        break;
    case SocialViewFeed:
        drawFeedView(canvas);
        break;
    case SocialViewMessageUsers:
        drawMessageUsersView(canvas);
        break;
    case SocialViewMessages:
        drawMessagesView(canvas);
        break;
    case SocialViewExplore:
        drawExploreView(canvas);
        break;
    case SocialViewPost:
        drawPostView(canvas);
        break;
    case SocialViewComments:
        drawCommentsView(canvas);
        break;
    default:
        canvas_draw_str(canvas, 0, 10, "View not implemented yet.");
        break;
    };
}

void FlipSocialRun::updateInput(int input)
{
    lastInput = input;
    debounceInput();
    switch (currentView)
    {
    case SocialViewMenu:
    {
        switch (lastInput)
        {
        case InputKeyBack:
            // return to menu
            shouldReturnToMenu = true;
            break;
        case InputKeyDown:
        case InputKeyLeft:
            if (currentMenuIndex == SocialViewPost)
            {
                currentMenuIndex = SocialViewFeed;
            }
            else if (currentMenuIndex == SocialViewMessageUsers)
            {
                currentMenuIndex = SocialViewPost;
                shouldDebounce = true;
            }
            else if (currentMenuIndex == SocialViewExplore)
            {
                currentMenuIndex = SocialViewMessageUsers;
                shouldDebounce = true;
            }
            else if (currentMenuIndex == SocialViewProfile)
            {
                currentMenuIndex = SocialViewExplore;
                shouldDebounce = true;
            }
            break;
        case InputKeyUp:
        case InputKeyRight:
            if (currentMenuIndex == SocialViewFeed)
            {
                currentMenuIndex = SocialViewPost;
                shouldDebounce = true;
            }
            else if (currentMenuIndex == SocialViewPost)
            {
                currentMenuIndex = SocialViewMessageUsers;
                shouldDebounce = true;
            }
            else if (currentMenuIndex == SocialViewMessageUsers)
            {
                currentMenuIndex = SocialViewExplore;
                shouldDebounce = true;
            }
            else if (currentMenuIndex == SocialViewExplore)
            {
                currentMenuIndex = SocialViewProfile;
            }
            break;
        case InputKeyOk:
            switch (currentMenuIndex)
            {
            case SocialViewFeed:
                currentView = SocialViewFeed;
                shouldDebounce = true;
                break;
            case SocialViewPost:
                currentView = SocialViewPost;
                shouldDebounce = true;
                break;
            case SocialViewMessageUsers:
                currentView = SocialViewMessageUsers;
                shouldDebounce = true;
                break;
            case SocialViewExplore:
                currentView = SocialViewExplore;
                shouldDebounce = true;
                break;
            case SocialViewProfile:
                if (userInfoStatus == UserInfoNotStarted || userInfoStatus == UserInfoRequestError)
                {
                    currentView = SocialViewUserInfo;
                    userInfoStatus = UserInfoWaiting;
                    userRequest(RequestTypeUserInfo);
                }
                else if (userInfoStatus == UserInfoSuccess)
                {
                    currentView = SocialViewProfile;
                }
                shouldDebounce = true;
                break;
            default:
                break;
            };
            break;
        default:
            break;
        }
        break;
    }
    case SocialViewFeed:
    {
        switch (lastInput)
        {
        case InputKeyBack:
            currentView = SocialViewMenu;
            shouldDebounce = true;
            break;
        case InputKeyDown:
            // Switch to comments view for current feed item
            currentView = SocialViewComments;
            commentsStatus = CommentsNotStarted;
            commentsIndex = 0;
            shouldDebounce = true;
            break;
        case InputKeyLeft:
            if (feedItemIndex > 0)
            {
                feedItemIndex--;
                shouldDebounce = true;
            }
            else
            {
                // If at the start of the feed, show previous page
                if (feedStatus == FeedSuccess && feedIteration > 1)
                {
                    feedIteration--;
                    feedItemIndex = MAX_FEED_ITEMS - 1;
                    // no need to load again since we already have the data
                }
            }
            break;
        case InputKeyRight:
            if (feedItemIndex < (MAX_FEED_ITEMS - 1))
            {
                feedItemIndex++;
                shouldDebounce = true;
            }
            else
            {
                // If at the end of the feed, request next page
                if (feedStatus == FeedSuccess)
                {
                    feedIteration++;
                    feedItemIndex = 0;
                    feedStatus = FeedWaiting;
                    userRequest(RequestTypeFeed);
                }
            }
            break;
        case InputKeyOk:
            userRequest(RequestTypeFlipPost);
            shouldDebounce = true;
            break;
        default:
            break;
        };
        break;
    }
    case SocialViewPost:
    {
        auto keyboard = viewManager->getKeyboard();
        if (postStatus == PostKeyboard)
        {
            if (keyboard)
            {
                if (keyboard->isFinished())
                {
                    auto storage = viewManager->getStorage();
                    auto response = keyboard->getResponse();
                    if (!storage.write(FLIP_SOCIAL_NEW_POST_PATH, response.c_str(), response.size()))
                    {
                        printf("Failed to save user's feed post.\n");
                        postStatus = PostParseError;
                    }
                    else
                    {
                        postStatus = PostWaiting;
                        userRequest(RequestTypePost);
                    }
                }
                if (lastInput != -1)
                {
                    shouldDebounce = true;
                }
            }
            if (lastInput == InputKeyBack)
            {
                postStatus = PostChoose;
                shouldDebounce = true;
                if (keyboard)
                {
                    keyboard->reset();
                }
            }
        }
        else
        {
            switch (lastInput)
            {
            case InputKeyBack:
                currentView = SocialViewMenu;
                shouldDebounce = true;
                break;
            case InputKeyLeft:
            case InputKeyDown:
                if (postIndex > 0)
                {
                    postIndex--;
                    shouldDebounce = true;
                }
                break;
            case InputKeyRight:
            case InputKeyUp:
                if (postIndex < (MAX_PRE_SAVED_MESSAGES - 1))
                {
                    postIndex++;
                    shouldDebounce = true;
                }
                break;
            case InputKeyOk:
                if (postIndex == 0) // New Post
                {
                    postStatus = PostKeyboard;
                    shouldDebounce = true;
                    if (keyboard)
                    {
                        keyboard->reset();
                    }
                }
                else
                {
                    char *selectedPost = (char *)malloc(128);
                    if (!selectedPost)
                    {
                        printf("updateInput: Failed to allocate memory for selectedPost.\n");
                        postStatus = PostParseError;
                        shouldDebounce = true;
                        return;
                    }
                    if (getSelectedPost(selectedPost, 128))
                    {
                        if (keyboard)
                        {
                            keyboard->setResponse(selectedPost);
                            postStatus = PostKeyboard;
                            shouldDebounce = true;
                        }
                    }
                    free(selectedPost);
                }
                break;
            default:
                break;
            };
        }
        break;
    }
    case SocialViewMessageUsers:
    {
        switch (lastInput)
        {
        case InputKeyBack:
            currentView = SocialViewMenu;
            shouldDebounce = true;
            break;
        case InputKeyLeft:
        case InputKeyDown:
            if (messageUserIndex > 0)
            {
                messageUserIndex--;
                shouldDebounce = true;
            }
            break;
        case InputKeyRight:
        case InputKeyUp:
            if (messageUserIndex < (MAX_MESSAGE_USERS - 1))
            {
                messageUserIndex++;
                shouldDebounce = true;
            }
            break;
        case InputKeyOk:
            currentView = SocialViewMessages;
            shouldDebounce = true;
            break;
        default:
            break;
        };
        break;
    }
    case SocialViewMessages:
    {
        if (messagesStatus == MessagesKeyboard)
        {
            auto keyboard = viewManager->getKeyboard();
            if (keyboard)
            {
                if (keyboard->isFinished())
                {
                    auto storage = viewManager->getStorage();
                    auto response = keyboard->getResponse();
                    if (!storage.write(FLIP_SOCIAL_MESSAGE_TO_USER_PATH, response.c_str(), response.size()))
                    {
                        printf("Failed to save user's message to storage.\n");
                        messagesStatus = MessagesParseError;
                    }
                    else
                    {
                        messagesStatus = MessagesSending;
                        userRequest(RequestTypeMessageSend);
                    }
                }
                if (lastInput != -1)
                {
                    shouldDebounce = true;
                }
            }
            if (lastInput == InputKeyBack)
            {
                messagesStatus = MessagesSuccess;
                shouldDebounce = true;
                if (keyboard)
                {
                    keyboard->reset();
                }
            }
        }
        else
        {
            switch (lastInput)
            {
            case InputKeyBack:
                currentView = SocialViewMessageUsers;
                messagesStatus = MessagesNotStarted;
                messagesIndex = 0;
                shouldDebounce = true;
                break;
            case InputKeyLeft:
            case InputKeyDown:
                // Navigate to previous message
                if (messagesIndex > 0)
                {
                    messagesIndex--;
                    shouldDebounce = true;
                }
                break;
            case InputKeyRight:
            case InputKeyUp:
                // Navigate to next message
                if (messagesIndex < (MAX_MESSAGES - 1))
                {
                    messagesIndex++;
                    shouldDebounce = true;
                }
                break;
            case InputKeyOk:
                messagesStatus = MessagesKeyboard;
                shouldDebounce = true;
                return;
            default:
                break;
            };
        }
        break;
    }
    case SocialViewExplore:
    {
        auto keyboard = viewManager->getKeyboard();
        if (exploreStatus == ExploreKeyboardUsers)
        {
            if (keyboard)
            {
                if (keyboard->isFinished())
                {
                    auto storage = viewManager->getStorage();
                    auto response = keyboard->getResponse();
                    if (!storage.write(FLIP_SOCIAL_EXPLORE_USER_PATH, response.c_str(), response.size()))
                    {
                        printf("Failed to save user's message to storage.\n");
                        exploreStatus = ExploreParseError;
                    }
                    else
                    {
                        printf("Searching for users matching: %s\n", response.c_str());
                        exploreStatus = ExploreWaiting;
                        exploreIndex = 0;
                        userRequest(RequestTypeExplore);
                    }
                }
                if (lastInput != -1)
                {
                    shouldDebounce = true;
                }
            }
            if (lastInput == InputKeyBack)
            {
                currentView = SocialViewMenu;
                exploreStatus = ExploreKeyboardUsers;
                exploreIndex = 0;
                shouldDebounce = true;
                if (keyboard)
                {
                    keyboard->reset();
                }
            }
        }
        else if (exploreStatus == ExploreKeyboardMessage)
        {
            if (keyboard)
            {
                if (keyboard->isFinished())
                {
                    auto storage = viewManager->getStorage();
                    auto response = keyboard->getResponse();
                    if (!storage.write(FLIP_SOCIAL_MESSAGE_TO_USER_PATH, response.c_str(), response.size()))
                    {
                        printf("Failed to save user's message to storage.\n");
                        exploreStatus = ExploreParseError;
                    }
                    else
                    {
                        exploreStatus = ExploreSending;
                        userRequest(RequestTypeMessageSend);
                    }
                }
                if (lastInput != -1)
                {
                    shouldDebounce = true;
                }
            }
            if (lastInput == InputKeyBack)
            {
                exploreStatus = ExploreSuccess;
                shouldDebounce = true;
                if (keyboard)
                {
                    keyboard->reset();
                }
            }
        }
        else
        {
            switch (lastInput)
            {
            case InputKeyBack:
                currentView = SocialViewMenu;
                exploreStatus = ExploreKeyboardUsers;
                exploreIndex = 0;
                shouldDebounce = true;
                if (keyboard)
                {
                    keyboard->reset();
                }
                break;
            case InputKeyLeft:
            case InputKeyDown:
                if (exploreIndex > 0)
                {
                    exploreIndex--;
                    shouldDebounce = true;
                }
                break;
            case InputKeyRight:
            case InputKeyUp:
                if (exploreIndex < (MAX_EXPLORE_USERS - 1))
                {
                    exploreIndex++;
                    shouldDebounce = true;
                }
                break;
            case InputKeyOk:
                exploreStatus = ExploreKeyboardMessage;
                shouldDebounce = true;
                if (keyboard)
                {
                    keyboard->reset();
                }
                return;
            default:
                break;
            };
        }
        break;
    }
    case SocialViewProfile:
    {
        switch (lastInput)
        {
        case InputKeyBack:
            currentView = SocialViewMenu;
            shouldDebounce = true;
            break;
        case InputKeyLeft:
        case InputKeyDown:
            if (currentProfileElement > 0)
            {
                currentProfileElement--;
                shouldDebounce = true;
            }
            break;
        case InputKeyRight:
        case InputKeyUp:
            if (currentProfileElement < (ProfileElementMAX - 1))
            {
                currentProfileElement++;
                shouldDebounce = true;
            }
            break;
        default:
            break;
        };
        break;
    }
    case SocialViewComments:
    {
        auto keyboard = viewManager->getKeyboard();
        if (commentsStatus == CommentsKeyboard)
        {
            if (keyboard)
            {
                if (keyboard->isFinished())
                {
                    auto storage = viewManager->getStorage();
                    auto response = keyboard->getResponse();
                    if (!storage.write(FLIP_SOCIAL_COMMENT_POST_PATH, response.c_str(), response.size()))
                    {
                        printf("Failed to save user's comment.\n");
                        commentsStatus = CommentsParseError;
                    }
                    else
                    {
                        commentsStatus = CommentsSending;
                        userRequest(RequestTypeCommentPost);
                    }
                }
                if (lastInput != -1)
                {
                    shouldDebounce = true;
                }
            }
            if (lastInput == InputKeyBack)
            {
                commentsStatus = CommentsSuccess;
                shouldDebounce = true;
                if (keyboard)
                {
                    keyboard->reset();
                }
            }
        }
        else
        {
            switch (lastInput)
            {
            case InputKeyBack:
                currentView = SocialViewFeed;
                commentIsValid = false;
                shouldDebounce = true;
                break;
            case InputKeyLeft:
                if (commentsIndex > 0)
                {
                    commentsIndex--;
                    shouldDebounce = true;
                }
                break;
            case InputKeyRight:
                if (commentsIndex < (MAX_COMMENTS - 1))
                {
                    commentsIndex++;
                    shouldDebounce = true;
                }
                break;
            case InputKeyDown:
                // Start reply to comment
                commentsStatus = CommentsKeyboard;
                if (keyboard)
                {
                    keyboard->reset();
                    keyboard->setResponse(""); // Start with empty text for reply
                }
                shouldDebounce = true;
                break;
            case InputKeyOk:
                // Flip the current comment
                if (commentIsValid)
                {
                    userRequest(RequestTypeCommentFlip);
                }
                shouldDebounce = true;
                break;
            default:
                break;
            }
        }
        break;
    }
    case SocialViewLogin:
    case SocialViewRegistration:
    case SocialViewUserInfo:
    {
        if (lastInput == InputKeyBack)
        {
            currentView = SocialViewLogin;
            shouldReturnToMenu = true;
            shouldDebounce = true;
        }
        break;
    }
    default:
        break;
    };
}

void FlipSocialRun::userRequest(RequestType requestType)
{
    if (!http)
    {
        http = std::make_unique<HTTP>();
    }
    else
    {
        http->clearAsyncResponse();
        http.reset();
        http = std::make_unique<HTTP>();
    }

    // Allocate memory for credentials
    std::string username = flipSocialUtilsLoadUserFromFlash(viewManager);
    std::string password = flipSocialUtilsLoadPasswordFromFlash(viewManager);

    if (username.empty() || password.empty())
    {
        switch (requestType)
        {
        case RequestTypeLogin:
            loginStatus = LoginCredentialsMissing;
            break;
        case RequestTypeRegistration:
            registrationStatus = RegistrationCredentialsMissing;
            break;
        case RequestTypeUserInfo:
            userInfoStatus = UserInfoCredentialsMissing;
            break;
        case RequestTypeFeed:
        case RequestTypeFlipPost:
        case RequestTypeCommentFetch:
        case RequestTypeCommentFlip:
        case RequestTypeCommentPost:
            feedStatus = FeedRequestError;
            break;
        case RequestTypeMessagesUserList:
            messageUsersStatus = MessageUsersRequestError;
            break;
        case RequestTypeMessagesWithUser:
            messagesStatus = MessagesRequestError;
            break;
        default:
            loginStatus = LoginRequestError;
            registrationStatus = RegistrationRequestError;
            userInfoStatus = UserInfoRequestError;
            feedStatus = FeedRequestError;
            messageUsersStatus = MessageUsersRequestError;
            break;
        }
        return;
    }

    std::map<std::string, std::string> headers;
    headers["Content-Type"] = "application/json";
    headers["HTTP_USER_AGENT"] = "Pico";
    headers["Setting"] = "X-Flipper-Redirect";
    headers["username"] = username.c_str();
    headers["password"] = password.c_str();

    // Create JSON payload for login/registration
    std::string payload = "{\"username\":\"" + username + "\",\"password\":\"" + password + "\"}";

    switch (requestType)
    {
    case RequestTypeLogin:
        if (!http->requestAsync("POST", "https://www.jblanked.com/flipper/api/user/login/", headers, payload.c_str()))
        {
            loginStatus = LoginRequestError;
        }
        break;
    case RequestTypeRegistration:
        if (!http->requestAsync("POST", "https://www.jblanked.com/flipper/api/user/register/", headers, payload.c_str()))
        {
            registrationStatus = RegistrationRequestError;
        }
        break;
    case RequestTypeUserInfo:
    {
        std::string url = "https://www.jblanked.com/flipper/api/user/profile/" + username + "/";
        if (!http->requestAsync("GET", url, headers))
        {
            userInfoStatus = UserInfoRequestError;
        }
        break;
    }
    case RequestTypeFeed:
    {
        std::string url = "https://www.jblanked.com/flipper/api/feed/" + std::to_string(MAX_FEED_ITEMS) + "/" + username + "/" + std::to_string(feedIteration) + "/max/series/";
        if (!http->requestAsync("GET", url, headers))
        {
            feedStatus = FeedRequestError;
        }
        break;
    }
    case RequestTypeFlipPost:
    {
        std::string feedPostPayload = "{\"username\":\"" + username + "\",\"post_id\":\"" + std::to_string(feedItemID) + "\"}";
        if (!http->requestAsync("POST", "https://www.jblanked.com/flipper/api/feed/flip/", headers, feedPostPayload))
        {
            feedStatus = FeedRequestError;
        }
        break;
    }
    case RequestTypeCommentFetch:
    {
        commentIsValid = false;
        std::string url = "https://www.jblanked.com/flipper/api/feed/comments/" + std::to_string(MAX_FEED_ITEMS) + "/" + username + "/" + std::to_string(feedItemID) + "/";
        std::string feedSaveName = "feed_" + std::to_string(feedIteration) + "_comments.txt";
        if (!http->requestAsync("GET", url, headers))
        {
            feedStatus = FeedRequestError;
        }
        break;
    }
    case RequestTypeCommentFlip:
    {
        std::string commentFlipPayload = "{\"username\":\"" + username + "\",\"post_id\":\"" + std::to_string(commentItemID) + "\"}";
        if (!http->requestAsync("POST", "https://www.jblanked.com/flipper/api/feed/flip/", headers, commentFlipPayload))
        {
            feedStatus = FeedRequestError;
        }
        break;
    }
    case RequestTypeMessagesUserList:
    {
        std::string url = "https://www.jblanked.com/flipper/api/messages/" + username + "/get/list/" + std::to_string(MAX_MESSAGE_USERS) + "/";
        if (!http->requestAsync("GET", url, headers))
        {
            messageUsersStatus = MessageUsersRequestError;
        }
        break;
    }
    case RequestTypeMessagesWithUser:
    {
        char *messageUser = (char *)malloc(64);
        if (!messageUser)
        {
            printf("userRequest: Failed to allocate memory for messageUser\n");
            messagesStatus = MessagesRequestError;
            return;
        }
        if (!getMessageUser(messageUser, 64))
        {
            printf("userRequest: Failed to get message user\n");
            messagesStatus = MessagesParseError;
            free(messageUser);
            return;
        }
        std::string url = "https://www.jblanked.com/flipper/api/messages/" + username + "/get/" + std::string(messageUser) + "/" + std::to_string(MAX_MESSAGES) + "/";
        if (!http->requestAsync("GET", url, headers))
        {
            messagesStatus = MessagesRequestError;
        }
        free(messageUser);
        break;
    }
    case RequestTypeMessageSend:
    {
        char *message = (char *)malloc(128);
        char *messageUser = (char *)malloc(64);
        if (!message || !messageUser)
        {
            printf("userRequest: Failed to allocate memory for message or messageUser.\n");
            messagesStatus = MessagesRequestError;
            if (message)
                free(message);
            if (messageUser)
                free(messageUser);
            return;
        }
        // Get message from user input
        auto storage = viewManager->getStorage();
        size_t bytes_read = 0;
        if (!storage.read(FLIP_SOCIAL_MESSAGE_TO_USER_PATH, message, 128, &bytes_read))
        {
            printf("Failed to load message to user.\n");
            free(message);
            free(messageUser);
            messagesStatus = MessagesRequestError;
            return;
        }
        message[bytes_read] = '\0'; // Ensure null termination at actual read length

        if (strlen(message) == 0 || strlen(message) > MAX_MESSAGE_LENGTH)
        {
            printf("userRequest: Message is empty or too long.\n");
            free(message);
            free(messageUser);
            messagesStatus = MessagesRequestError;
            return;
        }

        // Get the current message user
        if (!getMessageUser(messageUser, 64))
        {
            printf("userRequest: Failed to get message user\n");
            messagesStatus = MessagesParseError;
            free(message);
            free(messageUser);
            return;
        }
        std::string url = "https://www.jblanked.com/flipper/api/messages/" + username + "/post/";
        std::string payload = "{\"receiver\":\"" + std::string(messageUser) + "\",\"content\":\"" + std::string(message) + "\"}";
        if (!http->requestAsync("POST", url, headers, payload))
        {
            messagesStatus = MessagesRequestError;
        }
        free(message);
        free(messageUser);
        break;
    }
    case RequestTypeExplore:
    {
        char *keyword = (char *)malloc(64);
        if (!keyword)
        {
            printf("userRequest: Failed to allocate memory for keyword.\n");
            exploreStatus = ExploreRequestError;
            if (keyword)
                free(keyword);
            return;
        }
        // Get keyword from user input
        auto storage = viewManager->getStorage();
        size_t bytes_read = 0;
        if (!storage.read(FLIP_SOCIAL_EXPLORE_USER_PATH, keyword, 64, &bytes_read))
        {
            printf("userRequest: Failed to load explore user.\n");
            exploreStatus = ExploreRequestError;
            free(keyword);
            return;
        }
        keyword[bytes_read] = '\0'; // Ensure null termination at actual read length

        if (strlen(keyword) == 0 || strlen(keyword) > MAX_MESSAGE_LENGTH)
        {
            printf("userRequest: Explore user is empty or too long.\n");
            exploreStatus = ExploreRequestError;
            free(keyword);
            return;
        }

        std::string url = "https://www.jblanked.com/flipper/api/user/explore/" + std::string(keyword) + "/" + std::to_string(MAX_EXPLORE_USERS) + "/";
        if (!http->requestAsync("GET", url, headers))
        {
            exploreStatus = ExploreRequestError;
        }
        free(keyword);
        break;
    }
    case RequestTypePost:
    {
        char *userMessage = (char *)malloc(128);
        if (!userMessage)
        {
            printf("userRequest: Failed to allocate memory for userMessage.\n");
            postStatus = PostRequestError;
            return;
        }

        auto storage = viewManager->getStorage();
        size_t bytes_read = 0;
        if (!storage.read(FLIP_SOCIAL_NEW_POST_PATH, userMessage, 128, &bytes_read))
        {
            printf("Failed to load new feed post");
            postStatus = PostRequestError;
            free(userMessage);
            return;
        }
        userMessage[bytes_read] = '\0'; // Ensure null termination at actual read length

        std::string feedPost = "{\"username\":\"" + username + "\",\"content\":\"" + std::string(userMessage) + "\"}";
        if (!http->requestAsync("POST", "https://www.jblanked.com/flipper/api/feed/post/", headers, feedPost))
        {
            postStatus = PostRequestError;
        }
        free(userMessage);
        break;
    }
    case RequestTypeCommentPost:
    {
        char *userComment = (char *)malloc(128);
        if (!userComment)
        {
            printf("userRequest: Failed to allocate memory for userComment.\n");
            commentsStatus = CommentsRequestError;
            return;
        }

        auto storage = viewManager->getStorage();
        size_t bytes_read = 0;
        if (!storage.read(FLIP_SOCIAL_COMMENT_POST_PATH, userComment, 128, &bytes_read))
        {
            printf("Failed to load comment post");
            commentsStatus = CommentsRequestError;
            free(userComment);
            return;
        }
        userComment[bytes_read] = '\0'; // Ensure null termination at actual read length

        std::string commentPost = "{\"username\":\"" + username + "\",\"content\":\"" + std::string(userComment) + "\",\"post_id\":\"" + std::to_string(feedItemID) + "\"}";
        if (!http->requestAsync("POST", "https://www.jblanked.com/flipper/api/feed/comment/", headers, commentPost))
        {
            commentsStatus = CommentsRequestError;
        }
        free(userComment);
        break;
    }
    default:
        printf("Unknown request type: %d\n", requestType);
        loginStatus = LoginRequestError;
        registrationStatus = RegistrationRequestError;
        userInfoStatus = UserInfoRequestError;
        feedStatus = FeedRequestError;
        messageUsersStatus = MessageUsersRequestError;
        messagesStatus = MessagesRequestError;
        commentsStatus = CommentsRequestError;
        return;
    }
}