# picoware/apps/flip_social/run.py

from micropython import const
from picoware.system.vector import Vector
from picoware.system.colors import TFT_WHITE, TFT_BLACK

from json import loads as json_loads
from json import dumps as json_dumps

# social view constants
SOCIAL_VIEW_MENU = const(-1)  # main menu view
SOCIAL_VIEW_FEED = const(0)  # feed view
SOCIAL_VIEW_POST = const(1)  # post view
SOCIAL_VIEW_MESSAGE_USERS = const(2)  # (initial) messages view
SOCIAL_VIEW_EXPLORE = const(3)  # explore view
SOCIAL_VIEW_PROFILE = const(4)  # profile view
SOCIAL_VIEW_LOGIN = const(5)  # login view
SOCIAL_VIEW_REGISTRATION = const(6)  # registration view
SOCIAL_VIEW_USER_INFO = const(7)  # user info view
SOCIAL_VIEW_MESSAGES = const(8)  # messages view
SOCIAL_VIEW_COMMENTS = const(9)  # comments view

# login status constants
LOGIN_CREDENTIALS_MISSING = const(-1)  # Credentials missing
LOGIN_SUCCESS = const(0)  # Login successful
LOGIN_USER_NOT_FOUND = const(1)  # User not found
LOGIN_WRONG_PASSWORD = const(2)  # Wrong password
LOGIN_WAITING = const(3)  # Waiting for response
LOGIN_NOT_STARTED = const(4)  # Login not started
LOGIN_REQUEST_ERROR = const(5)  # Request error

# registration status constants
REGISTRATION_CREDENTIALS_MISSING = const(-1)  # Credentials missing
REGISTRATION_SUCCESS = const(0)  # Registration successful
REGISTRATION_USER_EXISTS = const(1)  # User already exists
REGISTRATION_REQUEST_ERROR = const(2)  # Request error
REGISTRATION_NOT_STARTED = const(3)  # Registration not started
REGISTRATION_WAITING = const(4)  # Waiting for response

# user info status constants
USER_INFO_CREDENTIALS_MISSING = const(-1)  # Credentials missing
USER_INFO_SUCCESS = const(0)  # User info retrieved successfully
USER_INFO_REQUEST_ERROR = const(1)  # Request error
USER_INFO_NOT_STARTED = const(2)  # User info not started
USER_INFO_WAITING = const(3)  # Waiting for response
USER_INFO_PARSE_ERROR = const(4)  # Error parsing user info

# request type constants
REQUEST_TYPE_LOGIN = const(0)  # Request login (login the user)
REQUEST_TYPE_REGISTRATION = const(1)  # Request registration (register the user)
REQUEST_TYPE_USER_INFO = const(2)  # Request user info (fetch user info)
REQUEST_TYPE_FEED = const(3)  # Request feed (fetch user feed)
REQUEST_TYPE_FLIP_POST = const(4)  # Request flip post (flip the current selected post)
REQUEST_TYPE_COMMENT_FETCH = const(5)  # Request comments (fetch comments for a post)
REQUEST_TYPE_COMMENT_POST = const(6)  # Request comment post (post a comment on a post)
REQUEST_TYPE_COMMENT_FLIP = const(7)  # Request comment flip (flip a comment)
REQUEST_TYPE_MESSAGES_USER_LIST = const(8)  # Request list of users who sent messages
REQUEST_TYPE_MESSAGES_WITH_USER = const(9)  # Request messages with a specific user
REQUEST_TYPE_MESSAGE_SEND = const(10)  # Request to send a message to the current user
REQUEST_TYPE_EXPLORE = const(11)  # Request explore (fetch users to explore)
REQUEST_TYPE_POST = const(12)  # Request post (send a post to the feed)

# profile element constants
PROFILE_ELEMENT_BIO = const(0)  # Bio element
PROFILE_ELEMENT_FRIENDS = const(1)  # Friends element
PROFILE_ELEMENT_JOINED = const(2)  # Joined element
PROFILE_ELEMENT_MAX = const(3)  # Max elements

# feed status constants
FEED_NOT_STARTED = const(0)  # Feed not started
FEED_WAITING = const(1)  # Waiting for response
FEED_SUCCESS = const(2)  # Feed retrieved successfully
FEED_PARSE_ERROR = const(3)  # Error parsing feed
FEED_REQUEST_ERROR = const(4)  # Error in feed request
FEED_FLIPPING = const(5)  # Flipping the current feed item

# message users status constants
MESSAGE_USERS_NOT_STARTED = const(0)  # Message users not started
MESSAGE_USERS_WAITING = const(1)  # Waiting for message users response
MESSAGE_USERS_SUCCESS = const(2)  # Message users fetched successfully
MESSAGE_USERS_PARSE_ERROR = const(3)  # Error parsing message users
MESSAGE_USERS_REQUEST_ERROR = const(4)  # Error in message users request

# messages status constants
MESSAGES_NOT_STARTED = const(0)  # Messages not started
MESSAGES_WAITING = const(1)  # Waiting for messages response
MESSAGES_SUCCESS = const(2)  # Messages fetched successfully
MESSAGES_PARSE_ERROR = const(3)  # Error parsing messages
MESSAGES_REQUEST_ERROR = const(4)  # Error in messages request
MESSAGES_KEYBOARD = const(5)  # Keyboard open for typing message
MESSAGES_SENDING = const(6)  # Sending message

# explore status constants
EXPLORE_NOT_STARTED = const(0)  # Explore not started
EXPLORE_WAITING = const(1)  # Waiting for explore response
EXPLORE_SUCCESS = const(2)  # Explore fetched successfully
EXPLORE_PARSE_ERROR = const(3)  # Error parsing explore
EXPLORE_REQUEST_ERROR = const(4)  # Error in explore request
EXPLORE_KEYBOARD_USERS = const(5)  # Keyboard for explore view (we'll start here)
EXPLORE_KEYBOARD_MESSAGE = const(6)  # Keyboard for sending message to user
EXPLORE_SENDING = const(7)  # Sending message in explore view

# post status constants
POST_NOT_STARTED = const(0)  # Post not started
POST_WAITING = const(1)  # Waiting for post response
POST_SUCCESS = const(2)  # Post sent successfully
POST_PARSE_ERROR = const(3)  # Error parsing post data
POST_REQUEST_ERROR = const(4)  # Error in post request
POST_KEYBOARD = const(5)  # Keyboard for post view (to create a new pre-saved post only)
POST_CHOOSE = const(6)  # Choosing a pre-saved post to send

# comments status constants
COMMENTS_NOT_STARTED = const(0)  # Comments not started
COMMENTS_WAITING = const(1)  # Waiting for comments response
COMMENTS_SUCCESS = const(2)  # Comments fetched successfully
COMMENTS_PARSE_ERROR = const(3)  # Error parsing comments
COMMENTS_REQUEST_ERROR = const(4)  # Error in comments request
COMMENTS_KEYBOARD = const(5)  # Keyboard for comments view (to type a new comment)
COMMENTS_SENDING = const(6)  # Sending comment

MAX_PRE_SAVED_MESSAGES = const(20)  # Maximum number of pre-saved messages
MAX_MESSAGE_LENGTH = const(100)  # Maximum length of a message in the feed
MAX_EXPLORE_USERS = const(50)  # Maximum number of users to explore
MAX_USER_LENGTH = const(32)  # Maximum length of a username
MAX_FRIENDS = const(50)  # Maximum number of friends
MAX_FEED_ITEMS = const(25)  # Maximum number of feed items
MAX_MESSAGE_USERS = const(40)  # Maximum number of users to display in the submenu
MAX_MESSAGES = const(20)  # Maximum number of messages between each user
MAX_COMMENTS = const(20)  # Maximum number of comments per feed item

def __safe_scale(canvas, x, y):
    """Scale (x, y) coordinates safely for older firmware.

    Returns 0 directly when a value is 0, since canvas.scale() on older
    firmware cannot handle zero values. Uses scale_x/scale_y for non-zero.
    """
    sx = 0 if x == 0 else canvas.scale_x(x)
    sy = 0 if y == 0 else canvas.scale_y(y)
    return sx, sy


class FlipSocialRun:
    """Class to manage the 'Run' view of FlipSocial"""

    def __init__(self, view_manager) -> None:
        from picoware.gui.loading import Loading
        from picoware.system.http import HTTP
        from picoware.system.settings import Settings

        _settings = Settings(view_manager.storage)
        self.username = _settings.server_settings.get("username")  # username from storage
        self.password = _settings.server_settings.get("password")  # password from storage

        self.comments_index: int = 0  # current comment index
        self.comment_is_valid: bool = False  # is the current comment valid
        self.comment_item_id: int = 0  # current comment item id
        self.comments_status: int = COMMENTS_NOT_STARTED  # current comments status
        self.current_menu_index: int = SOCIAL_VIEW_FEED  # current menu index
        self.current_profile_element: int = (
            PROFILE_ELEMENT_BIO  # current profile element
        )
        self.current_view: int = SOCIAL_VIEW_LOGIN  # current view
        self.explore_index: int = 0  # current explore menu index
        self.explore_status: int = EXPLORE_KEYBOARD_USERS  # current explore status
        self.feed_item_id: int = 0  # current feed item id
        self.feed_item_index: int = 0  # current feed item index
        self.feed_iteration: int = 1  # current feed iteration
        self.feed_status: int = FEED_NOT_STARTED  # current feed status
        self.http: HTTP = None  # http instance for requests
        self.input_held: bool = False  # is input held
        self.last_input: int = 0  # last input key pressed
        self.loading: Loading = None  # loading animation instance
        self.login_status: int = LOGIN_NOT_STARTED  # current login status
        self.messages_status: int = MESSAGES_NOT_STARTED  # current messages status
        self.message_users_status: int = (
            MESSAGE_USERS_NOT_STARTED  # current message users status
        )
        self.messages_index: int = 0  # index of the message in the messages submenu
        self.message_user_index: int = (
            0  # index of the user in the Message Users submenu
        )
        self.original_color_bg: int = 0  # original color of the draw instance
        self.original_color_fg: int = (
            0  # original foreground color of the draw instance
        )
        self.post_index: int = 0  # index of the post in the Post submenu
        self.post_status: int = POST_CHOOSE  # current post status
        self.registration_status: int = (
            REGISTRATION_NOT_STARTED  # current registration status
        )
        self.should_debounce: bool = False  # flag to debounce input
        self.should_return_to_menu: bool = False  # flag to return to main menu
        self.user_info_status: int = USER_INFO_NOT_STARTED  # current user info status

        # Private variables to replace bound method attributes
        self.__loading_started: bool = False  # loading started flag
        self.view_manager = view_manager  # reference to view manager
        self.keyboard_ran: bool = False  # has the keyboard run at least once
        self.should_clear_screen: bool = True  # should clear the screen

    def __del__(self) -> None:
        if self.http:
            del self.http
            self.http = None
        if self.loading:
            del self.loading
            self.loading = None

    @property
    def is_active(self) -> bool:
        """Check if the FlipSocialRun instance is active"""
        return self.should_return_to_menu is False

    def __loading_start(self, canvas, title: str) -> None:
        """Start the loading animation with the given title"""
        if not self.loading:
            from picoware.gui.loading import Loading

            self.loading = Loading(canvas, TFT_WHITE, TFT_BLACK)
            self.__loading_started = True
            if self.loading:
                self.loading.set_text(title)
        else:
            self.loading.set_text(title)

    def draw_comments_view(self, canvas) -> None:
        """Draw the comments view"""
        if self.comments_status == COMMENTS_WAITING:
            if not self.__loading_started:
                self.__loading_start(canvas, "Fetching...")
            if not self.http_request_is_finished():
                if self.loading:
                    self.loading.animate(False)
            else:
                from picoware.system.http import HTTP_ISSUE

                if (
                    not self.http
                    or self.http.state == HTTP_ISSUE
                    or not self.http.response
                ):
                    self.comments_status = COMMENTS_REQUEST_ERROR
                    self.feed_status = FEED_REQUEST_ERROR
                    if self.loading:
                        self.loading.stop()
                    self.__loading_started = False
                    return

                self.comments_status = COMMENTS_SUCCESS
                if self.loading:
                    self.loading.stop()
                self.__loading_started = False
        elif self.comments_status == COMMENTS_SUCCESS:
            if self.http and self.http.response:
                text_vec = Vector(0, 10)
                text_vec.x, text_vec.y = __safe_scale(canvas, 0, 10)
                if '"comments":[{' in self.http.response.text:
                    try:
                        obj = self.http.response.json()
                        if "comments" in obj and isinstance(obj["comments"], list):
                            comments = obj["comments"]
                            total_comments = len(comments)

                            if total_comments > 0:
                                self.comment_is_valid = True

                                # Display the current comment at commentsIndex
                                if self.comments_index < total_comments:
                                    comment = comments[self.comments_index]
                                    username = comment.get("username", "")
                                    message = comment.get("message", "")
                                    flipped = comment.get("flipped", "false")
                                    flips_str = str(comment.get("flip_count", 0))
                                    date_created = comment.get("date_created", "")
                                    comment_id = comment.get("id", 0)

                                    if username and message:
                                        self.comment_item_id = (
                                            int(comment_id) if comment_id else 0
                                        )
                                        self.draw_feed_item(
                                            canvas,
                                            username,
                                            message,
                                            flipped,
                                            flips_str,
                                            date_created,
                                            "0",
                                            True,
                                        )

                                        # Draw navigation arrows if there are multiple comments
                                        if self.comments_index > 0:
                                            text_vec.x, text_vec.y = __safe_scale(canvas, 2, 60)
                                            canvas._text(text_vec.x, text_vec.y, "< Prev", TFT_WHITE)
                                        if self.comments_index < total_comments - 1:
                                            text_vec.x, text_vec.y = __safe_scale(canvas, 
                                                96, 60
                                            )
                                            canvas._text(text_vec.x, text_vec.y, "Next >", TFT_WHITE)

                                        # Draw comment counter
                                        counter_text = f"{self.comments_index + 1}/{total_comments}"
                                        text_vec.x, text_vec.y = __safe_scale(canvas, 112, 10)
                                        canvas._text(text_vec.x, text_vec.y, counter_text, TFT_WHITE)
                                    else:
                                        self.comments_status = COMMENTS_PARSE_ERROR
                                        return
                                else:
                                    # If current comment index doesn't exist, go back to previous
                                    if self.comments_index > 0:
                                        self.comments_index -= 1
                            else:
                                text_vec.x, text_vec.y = __safe_scale(canvas, 0, 10)
                                canvas._text(text_vec.x, text_vec.y, "No comments found for this post.", TFT_WHITE)
                                text_vec.x, text_vec.y = __safe_scale(canvas, 0, 60)
                                canvas._text(text_vec.x, text_vec.y, "Be the first, click DOWN", TFT_WHITE)
                    except Exception as e:
                        self.view_manager.log(f"Error parsing comments: {e}")
                        self.comments_status = COMMENTS_PARSE_ERROR
                else:
                    text_vec.x, text_vec.y = __safe_scale(canvas, 0, 10)
                    canvas._text(text_vec.x, text_vec.y, "No comments found for this post.", TFT_WHITE)
                    text_vec.x, text_vec.y = __safe_scale(canvas, 0, 60)
                    canvas._text(text_vec.x, text_vec.y, "Be the first, click DOWN", TFT_WHITE)
        elif self.comments_status == COMMENTS_REQUEST_ERROR:
            text_vec = Vector(0, 10)
            text_vec.x, text_vec.y = __safe_scale(canvas, 0, 10)
            canvas._text(text_vec.x, text_vec.y, "Comments request failed!", TFT_WHITE)
            text_vec.y += 10
            canvas._text(text_vec.x, text_vec.y, "Check your network and", TFT_WHITE)
            text_vec.y += 10
            canvas._text(text_vec.x, text_vec.y, "try again later.", TFT_WHITE)
        elif self.comments_status == COMMENTS_PARSE_ERROR:
            text_vec = Vector(0, 10)
            text_vec.x, text_vec.y = __safe_scale(canvas, 0, 10)
            canvas._text(text_vec.x, text_vec.y, "Failed to parse comments!", TFT_WHITE)
            text_vec.y += 10
            canvas._text(text_vec.x, text_vec.y, "Try again...", TFT_WHITE)
        elif self.comments_status == COMMENTS_NOT_STARTED:
            self.comments_status = COMMENTS_WAITING
            self.user_request(REQUEST_TYPE_COMMENT_FETCH)
        elif self.comments_status == COMMENTS_KEYBOARD:
            keyboard = self.view_manager.keyboard
            if keyboard:
                self.should_clear_screen = False
                if not self.keyboard_ran:
                    keyboard.run(False, True)
                    keyboard.run(False, True)
                    self.keyboard_ran = True
                else:
                    keyboard.run(False, False)
        elif self.comments_status == COMMENTS_SENDING:
            if not self.__loading_started:
                self.__loading_start(canvas, "Sending...")
            if not self.http_request_is_finished():
                if self.loading:
                    self.loading.animate(False)
                else:
                    from picoware.gui.loading import Loading

                    self.loading = Loading(canvas, TFT_WHITE, TFT_BLACK)
            else:
                from picoware.system.http import HTTP_ISSUE

                if self.loading:
                    self.loading.stop()
                self.__loading_started = False

                if not self.http or self.http.state == HTTP_ISSUE:
                    self.comments_status = COMMENTS_REQUEST_ERROR
                    return

                if "[SUCCESS]" in self.http.response.text:
                    self.current_view = SOCIAL_VIEW_FEED
                    self.current_menu_index = SOCIAL_VIEW_FEED
                    self.comments_status = COMMENTS_NOT_STARTED
                    self.feed_status = FEED_NOT_STARTED
                    self.feed_item_index = 0
                    self.feed_iteration = 1
                else:
                    self.comments_status = COMMENTS_REQUEST_ERROR
        else:
            canvas._text(0, canvas.scale_x(10), "Loading comments...", TFT_WHITE)

    def draw_explore_view(self, canvas) -> None:
        """Draw the explore view"""

        if self.explore_status == EXPLORE_WAITING:
            if not self.__loading_started:
                self.__loading_start(canvas, "Fetching...")
            if not self.http_request_is_finished():
                if self.loading:
                    self.loading.animate(False)
            else:
                from picoware.system.http import HTTP_ISSUE

                if self.loading:
                    self.loading.stop()

                self.__loading_started = False

                if not self.http or self.http.state == HTTP_ISSUE:
                    self.explore_status = EXPLORE_REQUEST_ERROR
                    return

                response: str = self.http.response.text

                if response and "users" in response:
                    self.explore_status = EXPLORE_SUCCESS
                    storage = self.view_manager.storage
                    storage.write("picoware/flip_social/explore.json", response)
                    self.http.close()
                    return

                self.explore_status = EXPLORE_REQUEST_ERROR

        elif self.explore_status == EXPLORE_SUCCESS:
            storage = self.view_manager.storage
            data = storage.read("picoware/flip_social/explore.json")
            if data is None:
                canvas._text(0, canvas.scale_x(30), "Failed to load explore data.", TFT_WHITE)
                self.explore_status = EXPLORE_PARSE_ERROR
                return
            explore_users = []
            try:
                obj = json_loads(data)
                if "users" in obj and isinstance(obj["users"], list):
                    explore_users = obj["users"]
            except Exception:
                canvas._text(0, canvas.scale_x(30), "Failed to parse explore data.", TFT_WHITE)
                self.explore_status = EXPLORE_PARSE_ERROR
                return
            if not explore_users:
                canvas._text(0, canvas.scale_x(30), "No users to explore.", TFT_WHITE)
            else:
                self.draw_menu(canvas, self.explore_index, explore_users)
        elif self.explore_status == EXPLORE_REQUEST_ERROR:
            canvas._text(0, canvas.scale_x(10), "Messages request failed!", TFT_WHITE)
            canvas._text(0, canvas.scale_x(20), "Check your network and", TFT_WHITE)
            canvas._text(0, canvas.scale_x(30), "try again later.", TFT_WHITE)
        elif self.explore_status == EXPLORE_PARSE_ERROR:
            canvas._text(0, canvas.scale_x(10), "Error parsing messages!", TFT_WHITE)
            canvas._text(0, canvas.scale_x(20), "Try again...", TFT_WHITE)
        elif self.explore_status == EXPLORE_NOT_STARTED:
            self.explore_status = EXPLORE_WAITING
            self.user_request(REQUEST_TYPE_EXPLORE)
        elif self.explore_status == EXPLORE_KEYBOARD_USERS:
            keyboard = self.view_manager.keyboard
            if keyboard:
                self.should_clear_screen = False
                if not self.keyboard_ran:
                    keyboard.run(False, True)
                    keyboard.run(False, True)
                    self.keyboard_ran = True
                else:
                    keyboard.run(False, False)
        elif self.explore_status == EXPLORE_KEYBOARD_MESSAGE:
            keyboard = self.view_manager.keyboard
            if keyboard:
                self.should_clear_screen = False
                if not self.keyboard_ran:
                    keyboard.run(False, True)
                    keyboard.run(False, True)
                    self.keyboard_ran = True
                else:
                    keyboard.run(False, False)
        elif self.explore_status == EXPLORE_SENDING:
            if not self.__loading_started:
                self.__loading_start(canvas, "Sending...")
            if not self.http_request_is_finished():
                if self.loading:
                    self.loading.animate(False)
            else:
                from picoware.system.http import HTTP_ISSUE

                if self.loading:
                    self.loading.stop()
                self.__loading_started = False

                if not self.http or self.http.state == HTTP_ISSUE:
                    self.explore_status = EXPLORE_REQUEST_ERROR
                    return

                if "[SUCCESS]" in self.http.response.text:
                    self.current_view = SOCIAL_VIEW_MESSAGE_USERS
                    self.current_menu_index = SOCIAL_VIEW_MESSAGE_USERS
                    self.message_users_status = MESSAGE_USERS_NOT_STARTED
                    self.explore_status = EXPLORE_KEYBOARD_USERS
                    self.explore_index = 0
                    keyboard = self.view_manager.keyboard
                    self.keyboard_ran = False
                    if keyboard:
                        keyboard.reset()
                else:
                    self.explore_status = EXPLORE_REQUEST_ERROR
        else:
            canvas._text(0, canvas.scale_x(10), "Retrieving messages...", TFT_WHITE)

    def draw_feed_item(
        self,
        canvas,
        username: str,
        message: str,
        flipped: str,
        flips: str,
        date_created: str,
        comments: str,
        is_comment: bool = False,
    ) -> None:
        """Draw a single feed item"""
        is_flipped: bool = flipped == "true"
        is_admin: bool = username == "JBlanked"
        flip_count: int = int(flips) if flips.isdigit() else 0
        SH = canvas.size.y
        bottom_y = SH - canvas.scale_y(40)
        text_vec = Vector(0, 18)
        text_vec.x, text_vec.y = __safe_scale(canvas, 0, 18)
        if is_admin:
            # Filled white badge with black username text
            width = canvas.len(username) + 7
            height = canvas.get_font().height + 3
            canvas._fill_rectangle(text_vec.x, text_vec.y, width, height, TFT_WHITE)
            canvas._text(text_vec.x, text_vec.y, username, TFT_BLACK)

        else:
            canvas._text(text_vec.x, text_vec.y, username, TFT_WHITE)
        self.draw_feed_message(canvas, message, 0, 40)
        flip_message = "flip" if flip_count == 1 else "flips"
        canvas._text(0, bottom_y, f"{flip_count} {flip_message}", TFT_WHITE)
        flip_status = "Unflip" if is_flipped else "Flip"
        _x = canvas.scale_x(110 if is_flipped else 115)
        canvas._text(_x, bottom_y, flip_status, TFT_WHITE)
        if not is_comment:  # draw date in top-right corner
            if "minutes ago" in date_created:
                text_vec.x, text_vec.y = __safe_scale(canvas, 190, 18)
                canvas._text(text_vec.x, text_vec.y, date_created, TFT_WHITE)
            else:
                text_vec.x, text_vec.y = __safe_scale(canvas, 180, 18)
                canvas._text(text_vec.x, text_vec.y, date_created, TFT_WHITE)

            # draw down arrow icon and comment count
            _x = canvas.scale_x(170)
            canvas._text(_x, bottom_y, "Comment", TFT_WHITE)
            _x = canvas.scale_x(245)
            canvas._text(_x, bottom_y, f"({comments})", TFT_WHITE)

        else:
            # draw in bottom-right corner for comments
            _date_y = SH - canvas.scale_y(40)
            if "minutes ago" in date_created:
                _x = canvas.scale_x(190)
                canvas._text(_x, _date_y, date_created, TFT_WHITE)
            else:
                _x = canvas.scale_x(180)
                canvas._text(_x, _date_y, date_created, TFT_WHITE)

    def draw_feed_message(self, canvas, user_message: str, x: int, y: int) -> None:
        """Draw the feed message with wrapping"""
        if not user_message:
            self.view_manager.log("drawFeedMessage: No message to draw")
            return

        canvas._text(x, y, user_message, TFT_WHITE)

    def draw_feed_view(self, canvas) -> None:
        """Draw the feed view"""
        if self.feed_status == FEED_WAITING:
            if not self.__loading_started:
                self.__loading_start(canvas, "Fetching...")
            if not self.http_request_is_finished():
                if self.loading:
                    self.loading.animate(False)
            else:
                from picoware.system.http import HTTP_ISSUE

                if not self.http or self.http.state == HTTP_ISSUE:
                    self.feed_status = FEED_REQUEST_ERROR
                    if self.loading:
                        self.loading.stop()
                    self.__loading_started = False
                    return

                if self.http.response:
                    self.feed_status = FEED_SUCCESS
                    storage = self.view_manager.storage
                    storage.write(
                        "picoware/flip_social/feed.json", self.http.response.text
                    )
                    if self.loading:
                        self.loading.stop()
                    self.__loading_started = False
                    self.http.close()
                else:
                    self.feed_status = FEED_REQUEST_ERROR

        elif self.feed_status == FEED_SUCCESS:
            storage = self.view_manager.storage
            data = storage.read("picoware/flip_social/feed.json")
            if data:
                try:
                    obj = json_loads(data)
                    if "feed" in obj and isinstance(obj["feed"], list):
                        feed_items = obj["feed"]
                        if self.feed_item_index < len(feed_items):
                            item = feed_items[self.feed_item_index]
                            username = item.get("username", "")
                            message = item.get("message", "")
                            flipped = item.get("flipped", "false")
                            flips = str(item.get("flip_count", 0))
                            comments = str(item.get("comment_count", 0))
                            date_created = item.get("date_created", "")
                            item_id = item.get("id", 0)

                            if username and message:
                                self.feed_item_id = int(item_id) if item_id else 0
                                self.draw_feed_item(
                                    canvas,
                                    username,
                                    message,
                                    flipped,
                                    flips,
                                    date_created,
                                    comments,
                                    False,
                                )
                            else:
                                self.feed_status = FEED_PARSE_ERROR
                except Exception as e:
                    self.view_manager.log(f"Error parsing feed: {e}")
                    self.feed_status = FEED_PARSE_ERROR

        elif self.feed_status == FEED_REQUEST_ERROR:
            canvas._text(0, canvas.scale_x(10), "Feed request failed!", TFT_WHITE)
            canvas._text(0, canvas.scale_x(20), "Check your network and", TFT_WHITE)
            canvas._text(0, canvas.scale_x(30), "try again later.", TFT_WHITE)

        elif self.feed_status == FEED_PARSE_ERROR:
            canvas._text(0, canvas.scale_x(10), "Failed to parse feed!", TFT_WHITE)
            canvas._text(0, canvas.scale_x(20), "Try again...", TFT_WHITE)

        elif self.feed_status == FEED_NOT_STARTED:
            self.feed_status = FEED_WAITING
            self.user_request(REQUEST_TYPE_FEED)

        elif self.feed_status == FEED_FLIPPING:
            if not self.__loading_started:
                self.__loading_start(canvas, "Flipping...")
            if not self.http_request_is_finished():
                if self.loading:
                    self.loading.animate(False)
            else:
                from picoware.system.http import HTTP_ISSUE

                if self.loading:
                    self.loading.stop()
                self.__loading_started = False
                if not self.http or self.http.state == HTTP_ISSUE:
                    self.feed_status = FEED_REQUEST_ERROR
                    return
                if "[SUCCESS]" in self.http.response.text:
                    # increase the flip count locally for instant feedback
                    # and adjust the flipped status
                    storage = self.view_manager.storage
                    data = storage.read("picoware/flip_social/feed.json")
                    if data:
                        try:
                            obj = json_loads(data)
                            if "feed" in obj and isinstance(obj["feed"], list):
                                feed_items = obj["feed"]
                                if self.feed_item_index < len(feed_items):
                                    item = feed_items[self.feed_item_index]

                                    # Toggle flipped status
                                    was_flipped = item.get("flipped", "false") == "true"
                                    item["flipped"] = "false" if was_flipped else "true"

                                    # Update flip count
                                    flip_count = item.get("flip_count", 0)
                                    if was_flipped:
                                        item["flip_count"] = max(0, flip_count - 1)
                                    else:
                                        item["flip_count"] = flip_count + 1

                                    # Save updated feed back to storage
                                    updated_data = json_dumps(obj)
                                    storage.write(
                                        "picoware/flip_social/feed.json", updated_data
                                    )
                        except Exception as e:
                            self.view_manager.log(f"Error updating flip status: {e}")

                    self.feed_status = FEED_SUCCESS
                else:
                    self.feed_status = FEED_REQUEST_ERROR

        else:
            canvas.text(Vector(0, 10), "Loading feed...", TFT_WHITE)

    def draw_login_view(self, canvas) -> None:
        """Draw the login view"""

        if self.login_status == LOGIN_WAITING:
            if not self.__loading_started:
                self.__loading_start(canvas, "Logging in...")
            if not self.http_request_is_finished():
                if self.loading:
                    self.loading.animate(False)
            else:
                from picoware.system.http import HTTP_ISSUE

                if self.loading:
                    self.loading.stop()
                self.__loading_started = False

                if not self.http or self.http.state == HTTP_ISSUE:
                    self.login_status = LOGIN_REQUEST_ERROR
                    return

                response = self.http.response.text
                if response:
                    if "[SUCCESS]" in response:
                        self.login_status = LOGIN_SUCCESS
                        self.current_view = SOCIAL_VIEW_MENU
                        storage = self.view_manager.storage
                        storage.write("picoware/flip_social/login.json", '"success"')
                    elif "User not found" in response:
                        self.login_status = LOGIN_NOT_STARTED
                        self.current_view = SOCIAL_VIEW_REGISTRATION
                        self.registration_status = REGISTRATION_WAITING
                        self.user_request(REQUEST_TYPE_REGISTRATION)
                    elif "Incorrect password" in response:
                        self.login_status = LOGIN_WRONG_PASSWORD
                    elif "Username or password is empty" in response:
                        self.login_status = LOGIN_CREDENTIALS_MISSING
                    else:
                        self.login_status = LOGIN_REQUEST_ERROR
                else:
                    self.login_status = LOGIN_REQUEST_ERROR

        elif self.login_status == LOGIN_SUCCESS:
            canvas._text(0, canvas.scale_x(10), "Login successful!", TFT_WHITE)
            canvas._text(0, canvas.scale_x(20), "Press OK to continue.", TFT_WHITE)

        elif self.login_status == LOGIN_CREDENTIALS_MISSING:
            canvas._text(0, canvas.scale_x(10), "Missing credentials!", TFT_WHITE)
            canvas._text(0, canvas.scale_x(20), "Please set your username", TFT_WHITE)
            canvas._text(0, canvas.scale_x(30), "and password in the app.", TFT_WHITE)

        elif self.login_status == LOGIN_REQUEST_ERROR:
            canvas._text(0, canvas.scale_x(10), "Login request failed!", TFT_WHITE)
            canvas._text(0, canvas.scale_x(20), "Check your network and", TFT_WHITE)
            canvas._text(0, canvas.scale_x(30), "try again later.", TFT_WHITE)

        elif self.login_status == LOGIN_WRONG_PASSWORD:
            canvas._text(0, canvas.scale_x(10), "Wrong password!", TFT_WHITE)
            canvas._text(0, canvas.scale_x(20), "Please check your password", TFT_WHITE)
            canvas._text(0, canvas.scale_x(30), "and try again.", TFT_WHITE)

        elif self.login_status == LOGIN_NOT_STARTED:
            self.login_status = LOGIN_WAITING
            self.user_request(REQUEST_TYPE_LOGIN)

        else:
            canvas._text(0, canvas.scale_x(10), "Logging in...", TFT_WHITE)

    def draw_main_menu_view(self, canvas) -> None:
        """Draw the main menu view"""
        menu_items = ["Feed", "Post", "Messages", "Explore", "Profile"]
        self.draw_menu(canvas, self.current_menu_index, menu_items)

    def draw_menu(self, canvas, selected_index: int, menu_items: list) -> None:
        """Generic menu drawer"""
        SW = canvas.size.x

        # Draw title
        distance = canvas.scale_x(10)
        title = "FlipSocial"
        title_width = canvas.len(title)
        title_x = (SW - title_width) // 2
        _, _y = __safe_scale(canvas, 0, 25)
        canvas._text(title_x, _y, title, TFT_WHITE)

        # Draw underline
        _y += distance
        canvas._line(title_x, _y, title_x + title_width, _y, TFT_WHITE)

        # Draw decorative top pattern (full width)
        _y += (distance * 3)
        for i in range(0, SW + 1, 10):
            canvas._pixel(i, _y, TFT_WHITE)

        # Get current item
        if 0 <= selected_index < len(menu_items):
            current_item = menu_items[selected_index]

            menu_y = 160
            box_padding = canvas.scale_x(20)

            # Draw selection box 
            item_width = canvas.len(current_item)
            item_x = (SW - item_width) // 2
            box_w = item_width + box_padding * 2
            box_x = item_x - box_padding
            _, _box_y = __safe_scale(canvas, 0, menu_y - 20)
            _box_h = canvas.scale_y(40)
            canvas._fill_rectangle(box_x, _box_y, box_w, _box_h, TFT_WHITE)

            # Draw text centered (on top of the box)
            _, _text_y = __safe_scale(canvas, 0, menu_y - 10)
            canvas._text(item_x, _text_y, current_item, TFT_BLACK)

            # Draw navigation arrows
            if selected_index > 0:
                _x, _y = __safe_scale(canvas, 5, menu_y - 7)
                canvas._text(_x, _y, "<", TFT_WHITE)
            if selected_index < len(menu_items) - 1:
                _x = SW - canvas.scale_x(15)
                _, _y = __safe_scale(canvas, 0, menu_y - 7)
                canvas._text(_x, _y, ">", TFT_WHITE)

            # Draw indicator dots
            indicator_y = 195
            _dot_s = canvas.scale_x(10)
            _dot_spacing = canvas.scale_x(15)
            _dot_y = canvas.scale_y(indicator_y)
            if len(menu_items) <= 15:
                dots_start_x = (SW - (len(menu_items) * _dot_spacing)) // 2
                for i in range(len(menu_items)):
                    dot_x = dots_start_x + (i * _dot_spacing)
                    if i == selected_index:
                        canvas._fill_rectangle(
                            dot_x, _dot_y, _dot_s, _dot_s, TFT_WHITE
                        )
                    else:
                        canvas._rectangle(
                            dot_x, _dot_y, _dot_s, _dot_s, TFT_WHITE
                        )

            # Draw decorative bottom pattern (full width)
            _dot_y += _dot_s + _dot_spacing
            for i in range(0, SW + 1, 10):
                canvas._pixel(i, _dot_y, TFT_WHITE)

    def draw_messages_view(self, canvas) -> None:
        """Draw the messages view"""

        if self.messages_status == MESSAGES_WAITING:
            if not self.__loading_started:
                self.__loading_start(canvas, "Retrieving...")
            if not self.http_request_is_finished():
                if self.loading:
                    self.loading.animate(False)
            else:
                from picoware.system.http import HTTP_ISSUE

                if self.loading:
                    self.loading.stop()
                self.__loading_started = False

                if not self.http or self.http.state == HTTP_ISSUE:
                    self.messages_status = MESSAGES_REQUEST_ERROR
                    return

                if self.http.response and "conversations" in self.http.response.text:
                    self.messages_status = MESSAGES_SUCCESS
                else:
                    self.messages_status = MESSAGES_REQUEST_ERROR

        elif self.messages_status == MESSAGES_SUCCESS:
            if self.http and self.http.response:
                try:
                    obj: dict = json_loads(self.http.response.text)
                    if "conversations" in obj and isinstance(
                        obj["conversations"], list
                    ):
                        convos = obj["conversations"]
                        if self.messages_index > 0 and self.messages_index >= len(
                            convos
                        ):
                            self.messages_index = len(convos) - 1
                        if self.messages_index < len(convos):
                            msg = convos[self.messages_index]
                            sender = msg.get("sender", "")
                            content = msg.get("content", "")

                            if sender and content:
                                SW = canvas.size.x

                                # Draw title (sender name)
                                title_width = canvas.len(sender)
                                title_x = (SW - title_width) // 2
                                _, _y = __safe_scale(canvas, 0, 25)
                                canvas._text(title_x, _y, sender, TFT_WHITE)

                                # Draw underline for title
                                _, _y = __safe_scale(canvas, 0, 35)
                                canvas._line(title_x, _y, title_x + title_width, _y, TFT_WHITE)

                                # Draw decorative horizontal pattern (full width)
                                _, _decor_y = __safe_scale(canvas, 0, 45)
                                for i in range(0, SW + 1, 10):
                                    canvas._pixel(i, _decor_y, TFT_WHITE)

                                menu_y = 160

                                # Calculate content lines and box height
                                content_lines = 1
                                if len(content) > 30:
                                    content_lines = 2
                                if len(content) > 60:
                                    content_lines = 3

                                box_height = (content_lines * 20) + 20
                                box_height = max(box_height, 40)

                                box_y_offset = -45 if content_lines > 1 else -30

                                # Draw message content box
                                _x, _y = 25, menu_y + box_y_offset
                                _x, _y = __safe_scale(canvas, _x, _y)
                                _scaled_box_w = __safe_scale(canvas, 270, 0)[0]
                                _scaled_box_h = __safe_scale(canvas, 0, box_height)[1]
                                canvas._fill_rectangle(
                                    _x,
                                    _y,
                                    _scaled_box_w,
                                    _scaled_box_h,
                                    TFT_WHITE,
                                )

                                # Draw message content with word wrapping
                                if len(content) <= 30:
                                    # Single line
                                    line_width = canvas.len(content)
                                    line_x = (SW - line_width) // 2
                                    _, _y = __safe_scale(canvas, 0, menu_y + 10 - 20)
                                    canvas._text(line_x, _y, content, TFT_BLACK)
                                else:
                                    # Multi-line - break at word boundaries
                                    break_pos = content.rfind(" ", 0, 30)
                                    if break_pos != -1 and break_pos > 15:
                                        line1 = content[:break_pos]
                                        line2 = content[break_pos + 1 :]
                                        if len(line2) > 30:
                                            line2 = line2[:27] + "..."
                                    else:
                                        line1 = content[:30]
                                        line2 = (
                                            content[30:57] + "..."
                                            if len(content) > 30
                                            else ""
                                        )

                                    # Draw first line
                                    line1_width = canvas.len(line1)
                                    line1_x = (SW - line1_width) // 2
                                    _, _y = __safe_scale(canvas, 0, menu_y + 10 - 30)
                                    canvas._text(line1_x, _y, line1, TFT_BLACK)

                                    # Draw second line if it exists
                                    if line2:
                                        line2_width = canvas.len(line2)
                                        line2_x = (SW - line2_width) // 2
                                        _, _y = __safe_scale(canvas, 0, menu_y + 10 - 10)
                                        canvas._text(line2_x, _y, line2, TFT_BLACK)

                                # Navigation arrows
                                if self.messages_index > 0:
                                    _x, _y = __safe_scale(canvas, 5, menu_y - 7)
                                    canvas._text(_x, _y, "<", TFT_WHITE)
                                if self.messages_index < len(convos) - 1:
                                    _, _y = __safe_scale(canvas, 0, menu_y - 7)
                                    canvas._text(SW - canvas.scale_x(15), _y, ">", TFT_WHITE)

                                # Message counter
                                indicator_y = 195
                                total_messages = len(convos)
                                message_counter = (
                                    f"{self.messages_index + 1}/{total_messages}"
                                )
                                counter_width = canvas.len(message_counter)
                                counter_x = (SW - counter_width) // 2
                                _, _y = __safe_scale(canvas, 0, indicator_y)
                                canvas._text(counter_x, _y, message_counter, TFT_WHITE)

                                # Reply indicator
                                reply_text = "Press OK to Reply"
                                reply_width = canvas.len(reply_text)
                                reply_x = (SW - reply_width) // 2
                                _, _y = __safe_scale(canvas, 0, indicator_y + 25)
                                canvas._text(reply_x, _y, reply_text, TFT_WHITE)

                                # Draw decorative bottom pattern (full width)
                                _, _decor_y = __safe_scale(canvas, 0, 240)
                                for i in range(0, SW + 1, 10):
                                    canvas._pixel(i, _decor_y, TFT_WHITE)

                except Exception as e:
                    self.view_manager.log(f"Error parsing messages: {e}")
                    self.messages_status = MESSAGES_PARSE_ERROR

        elif self.messages_status == MESSAGES_REQUEST_ERROR:
            canvas._text(0, canvas.scale_x(10), "Messages request failed!", TFT_WHITE)
            canvas._text(0, canvas.scale_x(20), "Check your network and", TFT_WHITE)
            canvas._text(0, canvas.scale_x(30), "try again later.", TFT_WHITE)

        elif self.messages_status == MESSAGES_PARSE_ERROR:
            canvas._text(0, canvas.scale_x(10), "Error parsing messages!", TFT_WHITE)
            canvas._text(0, canvas.scale_x(20), "Try again...", TFT_WHITE)

        elif self.messages_status == MESSAGES_NOT_STARTED:
            self.messages_status = MESSAGES_WAITING
            self.user_request(REQUEST_TYPE_MESSAGES_WITH_USER)

        elif self.messages_status == MESSAGES_KEYBOARD:
            keyboard = self.view_manager.keyboard
            if keyboard:
                self.should_clear_screen = False
                if not self.keyboard_ran:
                    keyboard.run(False, True)
                    keyboard.run(False, True)
                    self.keyboard_ran = True
                else:
                    keyboard.run(False, False)

        elif self.messages_status == MESSAGES_SENDING:
            if not self.__loading_started:
                self.__loading_start(canvas, "Sending...")
            if not self.http_request_is_finished():
                if self.loading:
                    self.loading.animate(False)
            else:
                from picoware.system.http import HTTP_ISSUE

                if self.loading:
                    self.loading.stop()
                self.__loading_started = False
                self.keyboard_ran = False
                keyboard = self.view_manager.keyboard
                if keyboard:
                    keyboard.reset()

                if not self.http or self.http.state == HTTP_ISSUE:
                    self.messages_status = MESSAGES_REQUEST_ERROR
                    return

                if "[SUCCESS]" in self.http.response.text:
                    self.messages_status = MESSAGES_NOT_STARTED
                    self.messages_index = 0
                else:
                    self.messages_status = MESSAGES_REQUEST_ERROR

        else:
            canvas.text(Vector(0, 10), "Retrieving messages...", TFT_WHITE)

    def draw_message_users_view(self, canvas) -> None:
        """Draw the message users view"""

        if self.message_users_status == MESSAGE_USERS_WAITING:
            if not self.__loading_started:
                self.__loading_start(canvas, "Retrieving...")
            if not self.http_request_is_finished():
                if self.loading:
                    self.loading.animate(False)
            else:
                from picoware.system.http import HTTP_ISSUE

                if self.loading:
                    self.loading.stop()
                self.__loading_started = False

                if not self.http or self.http.state == HTTP_ISSUE:
                    self.message_users_status = MESSAGE_USERS_REQUEST_ERROR
                    return

                response = self.http.response.text
                if response and "users" in response:
                    self.message_users_status = MESSAGE_USERS_SUCCESS
                    storage = self.view_manager.storage
                    storage.write("picoware/flip_social/message_users.json", response)
                else:
                    self.message_users_status = MESSAGE_USERS_REQUEST_ERROR

        elif self.message_users_status == MESSAGE_USERS_SUCCESS:
            storage = self.view_manager.storage
            data = storage.read("picoware/flip_social/message_users.json")
            if data:
                try:
                    obj = json_loads(data)
                    if "users" in obj and isinstance(obj["users"], list):
                        users = obj["users"]
                        if users:
                            self.draw_menu(canvas, self.message_user_index, users)
                        else:
                            canvas.text(Vector(0, 30), "No messages found.", TFT_WHITE)
                except Exception as e:
                    self.view_manager.log(f"Error parsing message users: {e}")
                    self.message_users_status = MESSAGE_USERS_PARSE_ERROR
            else:
                canvas._text(0, canvas.scale_x(30), "Failed to load messages.", TFT_WHITE)

        elif self.message_users_status == MESSAGE_USERS_REQUEST_ERROR:
            canvas._text(0, canvas.scale_x(10), "Messages request failed!", TFT_WHITE)
            canvas._text(0, canvas.scale_x(20), "Check your network and", TFT_WHITE)
            canvas._text(0, canvas.scale_x(30), "try again later.", TFT_WHITE)

        elif self.message_users_status == MESSAGE_USERS_PARSE_ERROR:
            canvas._text(0, canvas.scale_x(10), "Error parsing messages!", TFT_WHITE)
            canvas._text(0, canvas.scale_x(20), "Try again...", TFT_WHITE)

        elif self.message_users_status == MESSAGE_USERS_NOT_STARTED:
            self.message_users_status = MESSAGE_USERS_WAITING
            self.user_request(REQUEST_TYPE_MESSAGES_USER_LIST)

        else:
            canvas._text(0, canvas.scale_x(10), "Retrieving messages...", TFT_WHITE)

    def draw_post_view(self, canvas) -> None:
        """Draw the post view"""
        if self.post_status == POST_WAITING:
            if not self.__loading_started:
                self.__loading_start(canvas, "Posting...")
            if not self.http_request_is_finished():
                if self.loading:
                    self.loading.animate(False)
            else:
                from picoware.system.http import HTTP_ISSUE

                if self.loading:
                    self.loading.stop()
                self.__loading_started = False
                self.keyboard_ran = False
                keyboard = self.view_manager.keyboard
                if keyboard:
                    keyboard.reset()

                if not self.http or self.http.state == HTTP_ISSUE:
                    self.post_status = POST_REQUEST_ERROR
                    return

                if "[SUCCESS]" in self.http.response.text:
                    self.post_status = POST_SUCCESS
                    self.current_view = SOCIAL_VIEW_FEED
                    self.current_menu_index = SOCIAL_VIEW_FEED
                    self.feed_status = FEED_NOT_STARTED
                    self.feed_iteration = 1
                    self.feed_item_index = 0
                else:
                    self.post_status = POST_REQUEST_ERROR

        elif self.post_status == POST_SUCCESS:
            canvas._text(0, canvas.scale_x(10), "Posted successfully!", TFT_WHITE)
            canvas._text(0, canvas.scale_x(20), "Press OK to continue.", TFT_WHITE)

        elif self.post_status == POST_REQUEST_ERROR:
            canvas._text(0, canvas.scale_x(10), "Post request failed!", TFT_WHITE)
            canvas._text(0, canvas.scale_x(20), "Ensure your message", TFT_WHITE)
            canvas._text(0, canvas.scale_x(30), "follows the rules.", TFT_WHITE)

        elif self.post_status == POST_PARSE_ERROR:
            canvas._text(0, canvas.scale_x(10), "Error parsing post!", TFT_WHITE)
            canvas._text(0, canvas.scale_x(20), "Ensure your message", TFT_WHITE)
            canvas._text(0, canvas.scale_x(30), "follows the rules.", TFT_WHITE)

        elif self.post_status == POST_KEYBOARD:
            keyboard = self.view_manager.keyboard
            if keyboard:
                self.should_clear_screen = False
                if not self.keyboard_ran:
                    keyboard.run(False, True)
                    keyboard.run(False, True)
                    self.keyboard_ran = True
                else:
                    keyboard.run(False, False)

        elif self.post_status == POST_CHOOSE:
            storage = self.view_manager.storage
            data = storage.read("picoware/flip_social/presaves.txt")

            menu_items = ["[New Post]"]
            if data:
                # Parse line-by-line
                lines = data.split("\n")
                for line in lines:
                    line = line.strip()
                    if line and len(menu_items) < MAX_PRE_SAVED_MESSAGES + 1:
                        menu_items.append(line)

            self.draw_menu(canvas, self.post_index, menu_items)

        else:
            canvas.text(Vector(0, 10), "Awaiting...", TFT_WHITE)

    def draw_profile_view(self, canvas) -> None:
        """Draw the profile view"""

        SW = canvas.size.x
        storage = self.view_manager.storage
        data = storage.read("picoware/flip_social/profile.json")
        vec = Vector(0, 0)

        if not data:
            vec.x, vec.y = __safe_scale(canvas, SW // 2 - 70, 80)
            canvas._text(vec.x, vec.y, "Failed to load user info.", TFT_WHITE)
            return

        if not self.username:
            vec.x, vec.y = __safe_scale(canvas, SW // 2 - 70, 80)
            canvas._text(vec.x, vec.y, "Failed to load username.", TFT_WHITE)
            return

        try:
            obj = json_loads(data)
            bio = obj.get("bio", "No bio")
            friends_count = str(obj.get("friends_count", 0))
            date_created = obj.get("date_created", "Unknown")

            # Draw title
            title_width = canvas.len(self.username)
            title_x = (SW - title_width) // 2
            _, _y = __safe_scale(canvas, 0, 25)
            canvas._text(title_x, _y, self.username, TFT_WHITE)

            # Draw underline
            _, _y = __safe_scale(canvas, 0, 35)
            canvas._line(title_x, _y, title_x + title_width, _y, TFT_WHITE)

            # Draw decorative pattern (full width)
            _, _decor_y = __safe_scale(canvas, 0, 45)
            for i in range(0, SW + 1, 10):
                canvas._pixel(i, _decor_y, TFT_WHITE)

            # Profile elements
            menu_y = 160
            vec.x, vec.y = __safe_scale(canvas, 25, menu_y - 20)
            _w, _h = __safe_scale(canvas, 270, 40)
            canvas._fill_rectangle(vec.x, vec.y, _w, _h, TFT_WHITE)

            # Draw content based on current element
            if self.current_profile_element == PROFILE_ELEMENT_BIO:
                content = bio if bio else "No bio"
            elif self.current_profile_element == PROFILE_ELEMENT_FRIENDS:
                content = friends_count
            elif self.current_profile_element == PROFILE_ELEMENT_JOINED:
                content = date_created
            else:
                content = "Unknown"

            content_width = canvas.len(content)
            content_x = (SW - content_width) // 2
            _, _y = __safe_scale(canvas, 0, menu_y - 10)
            canvas._text(content_x, _y, content, TFT_BLACK)

            # Navigation arrows
            if self.current_profile_element > 0:
                vec.x, vec.y = __safe_scale(canvas, 5, menu_y - 7)
                canvas._text(vec.x, vec.y, "<", TFT_WHITE)
            if self.current_profile_element < PROFILE_ELEMENT_MAX - 1:
                _, _y = __safe_scale(canvas, 0, menu_y - 7)
                canvas._text(SW - canvas.scale_x(15), _y, ">", TFT_WHITE)

            # Indicator dots
            indicator_y = 195
            _dot_s = canvas.scale_x(8)
            _dot_spacing = canvas.scale_x(15)
            _dot_y = canvas.scale_y(indicator_y)
            dots_start_x = (SW - (PROFILE_ELEMENT_MAX * _dot_spacing)) // 2
            for i in range(PROFILE_ELEMENT_MAX):
                dot_x = dots_start_x + (i * _dot_spacing)
                if i == self.current_profile_element:
                    canvas._fill_rectangle(
                        dot_x, _dot_y, _dot_s, _dot_s, TFT_WHITE
                    )
                else:
                    canvas._rectangle(dot_x, _dot_y, _dot_s, _dot_s, TFT_WHITE)

            # Draw decorative bottom pattern (full width)
            _, _decor_y = __safe_scale(canvas, 0, 210)
            for i in range(0, SW + 1, 10):
                canvas._pixel(i, _decor_y, TFT_WHITE)

        except Exception as e:
            self.view_manager.log(f"Error parsing profile: {e}")
            _, _y = __safe_scale(canvas, 0, 30)
            canvas._text(0, _y, "Incomplete profile data.", TFT_WHITE)

    def draw_registration_view(self, canvas) -> None:
        """Draw the registration view"""
        vec = Vector(0, 0)

        if self.registration_status == REGISTRATION_WAITING:
            if not self.__loading_started:
                self.__loading_start(canvas, "Registering...")
            if not self.http_request_is_finished():
                if self.loading:
                    self.loading.animate(False)
            else:
                from picoware.system.http import HTTP_ISSUE

                if self.loading:
                    self.loading.stop()
                self.__loading_started = False

                if not self.http or self.http.state == HTTP_ISSUE:
                    self.registration_status = REGISTRATION_REQUEST_ERROR
                    return

                response = self.http.response.text
                if response:
                    if "[SUCCESS]" in response:
                        self.registration_status = REGISTRATION_SUCCESS
                        self.current_view = SOCIAL_VIEW_MENU
                    elif "Username or password not provided" in response:
                        self.registration_status = REGISTRATION_CREDENTIALS_MISSING
                    elif "User already exists" in response:
                        self.registration_status = REGISTRATION_USER_EXISTS
                    else:
                        self.registration_status = REGISTRATION_REQUEST_ERROR
                else:
                    self.registration_status = REGISTRATION_REQUEST_ERROR

        elif self.registration_status == REGISTRATION_SUCCESS:
            vec.x, vec.y = __safe_scale(canvas, 0, 10)
            canvas.text(vec, "Registration successful!", TFT_WHITE)
            vec.x, vec.y = __safe_scale(canvas, 0, 20)
            canvas.text(vec, "Press OK to continue.", TFT_WHITE)

        elif self.registration_status == REGISTRATION_CREDENTIALS_MISSING:
            vec.x, vec.y = __safe_scale(canvas, 0, 10)
            canvas.text(vec, "Missing credentials!", TFT_WHITE)
            vec.x, vec.y = __safe_scale(canvas, 0, 20)
            canvas.text(vec, "Please set your username", TFT_WHITE)
            vec.x, vec.y = __safe_scale(canvas, 0, 30)
            canvas.text(vec, "and password in the app.", TFT_WHITE)

        elif self.registration_status == REGISTRATION_REQUEST_ERROR:
            vec.x, vec.y = __safe_scale(canvas, 0, 10)
            canvas.text(vec, "Registration failed!", TFT_WHITE)
            vec.x, vec.y = __safe_scale(canvas, 0, 20)
            canvas.text(vec, "Check your network and", TFT_WHITE)
            vec.x, vec.y = __safe_scale(canvas, 0, 30)
            canvas.text(vec, "try again later.", TFT_WHITE)

        else:
            vec.x, vec.y = __safe_scale(canvas, 0, 10)
            canvas.text(vec, "Registering...", TFT_WHITE)

    def draw_user_info_view(self, canvas) -> None:
        """Draw the user info view"""
        vec = Vector(0, 0)
        if self.user_info_status == USER_INFO_WAITING:
            if not self.__loading_started:
                self.__loading_start(canvas, "Syncing...")
            if not self.http_request_is_finished():
                if self.loading:
                    self.loading.animate(False)
            else:
                from picoware.system.http import HTTP_ISSUE

                if not self.http or self.http.state == HTTP_ISSUE:
                    self.user_info_status = USER_INFO_REQUEST_ERROR
                    if self.loading:
                        self.loading.stop()
                    self.__loading_started = False
                    return

                if self.http.response:
                    self.user_info_status = USER_INFO_SUCCESS

                    # Save user info
                    storage = self.view_manager.storage
                    storage.write(
                        "picoware/flip_social/profile.json", self.http.response.text
                    )

                    if self.loading:
                        self.loading.stop()
                    self.__loading_started = False
                    self.current_view = SOCIAL_VIEW_PROFILE
                else:
                    self.user_info_status = USER_INFO_REQUEST_ERROR

        elif self.user_info_status == USER_INFO_SUCCESS:
            vec.x, vec.y = __safe_scale(canvas, 0, 10)
            canvas.text(vec, "User info loaded!", TFT_WHITE)
            vec.x, vec.y = __safe_scale(canvas, 0, 20)
            canvas.text(vec, "Press OK to continue.", TFT_WHITE)

        elif self.user_info_status == USER_INFO_CREDENTIALS_MISSING:
            vec.x, vec.y = __safe_scale(canvas, 0, 10)
            canvas.text(vec, "Missing credentials!", TFT_WHITE)
            vec.x, vec.y = __safe_scale(canvas, 0, 20)
            canvas.text(vec, "Please update your username", TFT_WHITE)
            vec.x, vec.y = __safe_scale(canvas, 0, 30)
            canvas.text(vec, "and password in settings.", TFT_WHITE)

        elif self.user_info_status == USER_INFO_REQUEST_ERROR:
            vec.x, vec.y = __safe_scale(canvas, 0, 10)
            canvas.text(vec, "User info request failed!", TFT_WHITE)
            vec.x, vec.y = __safe_scale(canvas, 0, 20)
            canvas.text(vec, "Check your network and", TFT_WHITE)
            vec.x, vec.y = __safe_scale(canvas, 0, 30)
            canvas.text(vec, "try again later.", TFT_WHITE)

        elif self.user_info_status == USER_INFO_PARSE_ERROR:
            vec.x, vec.y = __safe_scale(canvas, 0, 10)
            canvas.text(vec, "Failed to parse user info!", TFT_WHITE)
            vec.x, vec.y = __safe_scale(canvas, 0, 20)
            canvas.text(vec, "Try again...", TFT_WHITE)

        else:
            vec.x, vec.y = __safe_scale(canvas, 0, 10)
            canvas.text(vec, "Loading user info...", TFT_WHITE)

    def draw_wrapped_bio(self, canvas, text: str, x: int, y: int) -> None:
        """Draw the bio text with wrapping"""
        vec = Vector(0, 0)
        if not text or len(text) == 0:
            vec.x, vec.y = 64, y + 2
            canvas.text(vec, "No bio", TFT_WHITE)
            return

        max_chars_per_line = 18
        text_len = len(text)

        if text_len <= max_chars_per_line:
            vec.x, vec.y = 64, y + 2
            canvas.text(vec, text, TFT_WHITE)
            return

        # First line
        line1_len = min(text_len, max_chars_per_line)
        break_point = line1_len

        # Try to break at word boundary
        if text_len > max_chars_per_line:
            for i in range(max_chars_per_line - 1, max(max_chars_per_line - 8, 0), -1):
                if text[i] == " ":
                    break_point = i
                    break

        line1 = text[:break_point]

        # Second line
        if text_len > break_point:
            remaining_start = (
                break_point + 1 if text[break_point] == " " else break_point
            )
            remaining = text[remaining_start:]
            line2_len = min(len(remaining), max_chars_per_line)

            if len(remaining) > max_chars_per_line:
                line2 = remaining[: max_chars_per_line - 3] + "..."
            else:
                line2 = remaining[:line2_len]

            vec.x, vec.y = x, y
            canvas.text(vec, line1, TFT_WHITE)
            vec.y += 8
            canvas.text(vec, line2, TFT_WHITE)
        else:
            vec.x, vec.y = x, y
            canvas.text(vec, line1, TFT_WHITE)

    def get_message_user(self) -> str:
        """Get the message user at the specified messageUserIndex"""
        storage = self.view_manager.storage
        file_path = (
            "picoware/flip_social/explore.json"
            if self.current_menu_index == SOCIAL_VIEW_EXPLORE
            else "picoware/flip_social/message_users.json"
        )
        data = storage.read(file_path)

        if not data:
            self.view_manager.log("Failed to load message user list from storage")
            return ""

        try:
            obj = json_loads(data)
            if "users" in obj and isinstance(obj["users"], list):
                users = obj["users"]
                index = (
                    self.explore_index
                    if self.current_menu_index == SOCIAL_VIEW_EXPLORE
                    else self.message_user_index
                )
                if 0 <= index < len(users):
                    return users[index]
        except Exception as e:
            self.view_manager.log(f"Error parsing message user list: {e}")

        return ""

    def get_selected_post(self) -> str:
        """Get the selected post at the specified postIndex"""
        if self.post_index == 0:
            return "[New Post]"

        storage = self.view_manager.storage
        data = storage.read("picoware/flip_social/presaves.txt")

        if not data:
            self.view_manager.log("Failed to load pre-saved messages")
            return ""

        # Parse line by line
        lines = data.split("\n")
        post_count = 0
        for line in lines:
            line = line.strip()
            if line:
                if post_count == self.post_index - 1:
                    return line
                post_count += 1

        return ""

    def http_request_is_finished(self) -> bool:
        """Check if the HTTP request is finished"""
        if not self.http:
            return True
        from picoware.system.http import HTTP_IDLE, HTTP_ISSUE

        return self.http.state in (HTTP_IDLE, HTTP_ISSUE)

    def user_request(self, request_type: int) -> None:
        """Send a user request to the server based on the request type"""
        from picoware.system.http import HTTP

        if self.http:
            del self.http
            self.http = None

        self.http = HTTP(thread_manager=self.view_manager.thread_manager)

        if not self.username or not self.password:
            if request_type == REQUEST_TYPE_LOGIN:
                self.login_status = LOGIN_CREDENTIALS_MISSING
            elif request_type == REQUEST_TYPE_REGISTRATION:
                self.registration_status = REGISTRATION_CREDENTIALS_MISSING
            elif request_type == REQUEST_TYPE_USER_INFO:
                self.user_info_status = USER_INFO_CREDENTIALS_MISSING
            elif request_type in (
                REQUEST_TYPE_FEED,
                REQUEST_TYPE_FLIP_POST,
                REQUEST_TYPE_COMMENT_FETCH,
                REQUEST_TYPE_COMMENT_FLIP,
                REQUEST_TYPE_COMMENT_POST,
            ):
                self.feed_status = FEED_REQUEST_ERROR
            elif request_type == REQUEST_TYPE_MESSAGES_USER_LIST:
                self.message_users_status = MESSAGE_USERS_REQUEST_ERROR
            elif request_type == REQUEST_TYPE_MESSAGES_WITH_USER:
                self.messages_status = MESSAGES_REQUEST_ERROR
            return

        # Prepare headers
        headers = {
            "Content-Type": "application/json",
            "HTTP_USER_AGENT": "Pico",
            "Setting": "X-Flipper-Redirect",
            "username": self.username,
            "password": self.password,
            "User-Agent": "Raspberry Pi Pico W",
        }

        # Handle different request types
        storage = self.view_manager.storage

        if request_type == REQUEST_TYPE_LOGIN:
            payload = '{"username":"' + self.username + '","password":"' + self.password + '"}'
            if not self.http.post_async(
                "https://www.jblanked.com/flipper/api/user/login/", json_dumps(payload), headers
            ):
                self.view_manager.log(self.http.error)
                self.login_status = LOGIN_REQUEST_ERROR

        elif request_type == REQUEST_TYPE_REGISTRATION:
            payload = '{"username":"' + self.username + '","password":"' + self.password + '"}'
            if not self.http.post_async(
                "https://www.jblanked.com/flipper/api/user/register/", json_dumps(payload), headers
            ):
                self.view_manager.log(self.http.error)
                self.registration_status = REGISTRATION_REQUEST_ERROR

        elif request_type == REQUEST_TYPE_USER_INFO:
            url = "https://www.jblanked.com/flipper/api/user/profile/" + self.username + "/"
            if not self.http.get_async(url, headers):
                self.view_manager.log(self.http.error)
                self.user_info_status = USER_INFO_REQUEST_ERROR

        elif request_type == REQUEST_TYPE_FEED:
            url = (
                "https://www.jblanked.com/flipper/api/feed/"
                + str(MAX_FEED_ITEMS)
                + "/"
                + self.username
                + "/"
                + str(self.feed_iteration)
                + "/max/series/"
            )
            if not self.http.get_async(url, headers):
                self.view_manager.log(self.http.error)
                self.feed_status = FEED_REQUEST_ERROR

        elif request_type == REQUEST_TYPE_FLIP_POST:
            payload = {"username": self.username, "post_id": str(self.feed_item_id)}
            if not self.http.post_async(
                "https://www.jblanked.com/flipper/api/feed/flip/", json_dumps(payload), headers
            ):
                self.view_manager.log(self.http.error)
                self.feed_status = FEED_REQUEST_ERROR

        elif request_type == REQUEST_TYPE_COMMENT_FETCH:
            self.comment_is_valid = False
            url = (
                "https://www.jblanked.com/flipper/api/feed/comments/"
                + str(MAX_FEED_ITEMS)
                + "/"
                + self.username
                + "/"
                + str(self.feed_item_id)
                + "/"
            )
            if not self.http.get_async(url, headers):
                self.view_manager.log(self.http.error)
                self.feed_status = FEED_REQUEST_ERROR

        elif request_type == REQUEST_TYPE_COMMENT_FLIP:
            payload = (
                '{"username":"'
                + self.username
                + '","post_id":"'
                + str(self.comment_item_id)
                + '"}'
            )
            if not self.http.post_async(
                "https://www.jblanked.com/flipper/api/feed/flip/", payload, headers
            ):
                self.view_manager.log(self.http.error)
                self.feed_status = FEED_REQUEST_ERROR

        elif request_type == REQUEST_TYPE_MESSAGES_USER_LIST:
            url = (
                "https://www.jblanked.com/flipper/api/messages/"
                + self.username
                + "/get/list/"
                + str(MAX_MESSAGE_USERS)
                + "/"
            )
            if not self.http.get_async(url, headers):
                self.view_manager.log(self.http.error)
                self.message_users_status = MESSAGE_USERS_REQUEST_ERROR

        elif request_type == REQUEST_TYPE_MESSAGES_WITH_USER:
            message_user = self.get_message_user()
            if not message_user:
                self.messages_status = MESSAGES_PARSE_ERROR
                return
            url = (
                "https://www.jblanked.com/flipper/api/messages/"
                + self.username
                + "/get/"
                + message_user
                + "/"
                + str(MAX_MESSAGES)
                + "/"
            )
            if not self.http.get_async(url, headers):
                self.view_manager.log(self.http.error)
                self.messages_status = MESSAGES_REQUEST_ERROR

        elif request_type == REQUEST_TYPE_MESSAGE_SEND:
            message = storage.read("picoware/flip_social/message_to_user.txt")
            if not message or len(message) == 0 or len(message) > MAX_MESSAGE_LENGTH:
                self.messages_status = MESSAGES_REQUEST_ERROR
                return

            message_user = self.get_message_user()
            if not message_user:
                self.messages_status = MESSAGES_PARSE_ERROR
                return

            url = "https://www.jblanked.com/flipper/api/messages/" + self.username + "/post/"
            payload = {"receiver": message_user, "content": message}
            if not self.http.post_async(url, json_dumps(payload), headers):
                self.view_manager.log(self.http.error)
                self.messages_status = MESSAGES_REQUEST_ERROR

        elif request_type == REQUEST_TYPE_EXPLORE:
            keyword = storage.read("picoware/flip_social/explore_user.txt")
            if not keyword or len(keyword) == 0 or len(keyword) > MAX_MESSAGE_LENGTH:
                self.explore_status = EXPLORE_REQUEST_ERROR
                return

            url = (
                "https://www.jblanked.com/flipper/api/user/explore/"
                + keyword
                + "/"
                + str(MAX_EXPLORE_USERS)
                + "/"
            )
            if not self.http.get_async(url, headers):
                self.view_manager.log(self.http.error)
                self.explore_status = EXPLORE_REQUEST_ERROR

        elif request_type == REQUEST_TYPE_POST:
            user_message = storage.read("picoware/flip_social/new_post.txt")
            if not user_message:
                self.post_status = POST_REQUEST_ERROR
                return

            payload = {"username": self.username, "content": user_message}
            if not self.http.post_async(
                "https://www.jblanked.com/flipper/api/feed/post/", json_dumps(payload), headers
            ):
                self.view_manager.log(self.http.error)
                self.post_status = POST_REQUEST_ERROR

        elif request_type == REQUEST_TYPE_COMMENT_POST:
            user_comment = storage.read("picoware/flip_social/comment_post.txt")
            if not user_comment:
                self.comments_status = COMMENTS_REQUEST_ERROR
                return

            payload = {
                "username": self.username,
                "content": user_comment,
                "post_id": str(self.feed_item_id),
            }
            if not self.http.post_async(
                "https://www.jblanked.com/flipper/api/feed/comment/", json_dumps(payload), headers
            ):
                self.view_manager.log(self.http.error)
                self.comments_status = COMMENTS_REQUEST_ERROR
        else:
            self.view_manager.log(f"Unknown request type: {request_type}")
            self.login_status = LOGIN_REQUEST_ERROR
            self.registration_status = REGISTRATION_REQUEST_ERROR
            self.user_info_status = USER_INFO_REQUEST_ERROR
            self.feed_status = FEED_REQUEST_ERROR
            self.message_users_status = MESSAGE_USERS_REQUEST_ERROR
            self.messages_status = MESSAGES_REQUEST_ERROR
            self.explore_status = EXPLORE_REQUEST_ERROR
            self.post_status = POST_REQUEST_ERROR
            self.comments_status = COMMENTS_REQUEST_ERROR

    def start(self, view_manager) -> bool:
        """Start the FlipSocial run view"""

        # Only initialize once - don't reset view if already started
        if hasattr(self, "_started") and self._started:
            return True

        self._started = True
        self.original_color_bg = view_manager.background_color
        self.original_color_fg = view_manager.foreground_color
        view_manager.background_color = TFT_BLACK
        view_manager.foreground_color = TFT_WHITE

        # update login status
        storage = view_manager.storage
        data = storage.read("picoware/flip_social/login.json")
        if data and "success" in data:
            self.login_status = LOGIN_SUCCESS
            self.current_view = SOCIAL_VIEW_MENU
        else:
            self.login_status = LOGIN_NOT_STARTED
            self.current_view = SOCIAL_VIEW_LOGIN

        return True

    def run(self, view_manager) -> None:
        """Run the FlipSocial run view"""
        if not self.is_active:
            view_manager.back()
            return
        draw = view_manager.draw
        self.update_draw(draw)
        inp = view_manager.input_manager
        self.update_input(inp.button)
        inp.reset()
        draw.swap()

    def stop(self, view_manager) -> None:
        """Stop the FlipSocial run view"""
        view_manager.background_color = self.original_color_bg
        view_manager.foreground_color = self.original_color_fg

    def update_draw(self, draw) -> None:
        """Update and draw the run view"""
        if self.should_clear_screen:
            draw.fill_screen(TFT_BLACK)  # black background

        if self.current_view == SOCIAL_VIEW_MENU:
            self.draw_main_menu_view(draw)
        elif self.current_view == SOCIAL_VIEW_LOGIN:
            self.draw_login_view(draw)
        elif self.current_view == SOCIAL_VIEW_REGISTRATION:
            self.draw_registration_view(draw)
        elif self.current_view == SOCIAL_VIEW_USER_INFO:
            self.draw_user_info_view(draw)
        elif self.current_view == SOCIAL_VIEW_PROFILE:
            self.draw_profile_view(draw)
        elif self.current_view == SOCIAL_VIEW_FEED:
            self.draw_feed_view(draw)
        elif self.current_view == SOCIAL_VIEW_MESSAGE_USERS:
            self.draw_message_users_view(draw)
        elif self.current_view == SOCIAL_VIEW_MESSAGES:
            self.draw_messages_view(draw)
        elif self.current_view == SOCIAL_VIEW_EXPLORE:
            self.draw_explore_view(draw)
        elif self.current_view == SOCIAL_VIEW_POST:
            self.draw_post_view(draw)
        elif self.current_view == SOCIAL_VIEW_COMMENTS:
            self.draw_comments_view(draw)
        else:
            draw.text(Vector(0, 10), "View not implemented", TFT_WHITE)

    def update_input(self, input_key: int) -> None:
        """Update input state"""
        from picoware.system.buttons import (
            BUTTON_BACK,
            BUTTON_UP,
            BUTTON_DOWN,
            BUTTON_LEFT,
            BUTTON_RIGHT,
            BUTTON_CENTER,
        )

        self.should_debounce = False
        self.last_input = input_key

        if self.current_view == SOCIAL_VIEW_MENU:
            if self.last_input == BUTTON_BACK:
                self.should_return_to_menu = True
            elif self.last_input in (BUTTON_DOWN, BUTTON_LEFT):
                if self.current_menu_index == SOCIAL_VIEW_POST:
                    self.current_menu_index = SOCIAL_VIEW_FEED
                elif self.current_menu_index == SOCIAL_VIEW_MESSAGE_USERS:
                    self.current_menu_index = SOCIAL_VIEW_POST
                    self.should_debounce = True
                elif self.current_menu_index == SOCIAL_VIEW_EXPLORE:
                    self.current_menu_index = SOCIAL_VIEW_MESSAGE_USERS
                    self.should_debounce = True
                elif self.current_menu_index == SOCIAL_VIEW_PROFILE:
                    self.current_menu_index = SOCIAL_VIEW_EXPLORE
                    self.should_debounce = True
            elif self.last_input in (BUTTON_UP, BUTTON_RIGHT):
                if self.current_menu_index == SOCIAL_VIEW_FEED:
                    self.current_menu_index = SOCIAL_VIEW_POST
                    self.should_debounce = True
                elif self.current_menu_index == SOCIAL_VIEW_POST:
                    self.current_menu_index = SOCIAL_VIEW_MESSAGE_USERS
                    self.should_debounce = True
                elif self.current_menu_index == SOCIAL_VIEW_MESSAGE_USERS:
                    self.current_menu_index = SOCIAL_VIEW_EXPLORE
                    self.should_debounce = True
                elif self.current_menu_index == SOCIAL_VIEW_EXPLORE:
                    self.current_menu_index = SOCIAL_VIEW_PROFILE
            elif self.last_input == BUTTON_CENTER:
                if self.current_menu_index == SOCIAL_VIEW_FEED:
                    self.current_view = SOCIAL_VIEW_FEED
                    self.should_debounce = True
                elif self.current_menu_index == SOCIAL_VIEW_POST:
                    self.current_view = SOCIAL_VIEW_POST
                    self.should_debounce = True
                    self.last_input = -1
                    return
                elif self.current_menu_index == SOCIAL_VIEW_MESSAGE_USERS:
                    self.current_view = SOCIAL_VIEW_MESSAGE_USERS
                    self.should_debounce = True
                    self.last_input = -1
                    return
                elif self.current_menu_index == SOCIAL_VIEW_EXPLORE:
                    self.current_view = SOCIAL_VIEW_EXPLORE
                    self.should_debounce = True
                    self.last_input = -1
                    return
                elif self.current_menu_index == SOCIAL_VIEW_PROFILE:
                    if self.user_info_status in (
                        USER_INFO_NOT_STARTED,
                        USER_INFO_REQUEST_ERROR,
                    ):
                        self.current_view = SOCIAL_VIEW_USER_INFO
                        self.user_info_status = USER_INFO_WAITING
                        self.user_request(REQUEST_TYPE_USER_INFO)
                    elif self.user_info_status == USER_INFO_SUCCESS:
                        self.current_view = SOCIAL_VIEW_PROFILE
                    self.should_debounce = True
                    self.last_input = -1
                    return

        elif self.current_view == SOCIAL_VIEW_FEED:
            if self.last_input == BUTTON_BACK:
                self.current_view = SOCIAL_VIEW_MENU
                self.should_debounce = True
            elif self.last_input == BUTTON_DOWN:
                self.current_view = SOCIAL_VIEW_COMMENTS
                self.comments_status = COMMENTS_NOT_STARTED
                self.comments_index = 0
                self.should_debounce = True
            elif self.last_input == BUTTON_LEFT:
                if self.feed_item_index > 0:
                    self.feed_item_index -= 1
                    self.should_debounce = True
                elif self.feed_status == FEED_SUCCESS and self.feed_iteration > 1:
                    self.feed_iteration -= 1
                    self.feed_item_index = MAX_FEED_ITEMS - 1
            elif self.last_input == BUTTON_RIGHT:
                if self.feed_item_index < MAX_FEED_ITEMS - 1:
                    self.feed_item_index += 1
                    self.should_debounce = True
                elif self.feed_status == FEED_SUCCESS:
                    self.feed_iteration += 1
                    self.feed_item_index = 0
                    self.feed_status = FEED_WAITING
                    self.user_request(REQUEST_TYPE_FEED)
            elif self.last_input == BUTTON_CENTER:
                self.user_request(REQUEST_TYPE_FLIP_POST)
                self.feed_status = FEED_FLIPPING
                self.should_debounce = True

        elif self.current_view == SOCIAL_VIEW_POST:
            keyboard = self.view_manager.keyboard
            if self.post_status == POST_KEYBOARD:
                if keyboard and keyboard.is_finished:
                    self.keyboard_ran = False
                    self.should_clear_screen = True
                    response = keyboard.response
                    storage = self.view_manager.storage
                    storage.write("picoware/flip_social/new_post.txt", response)
                    self.post_status = POST_WAITING
                    self.user_request(REQUEST_TYPE_POST)
                if self.last_input != -1:
                    self.should_debounce = True
                if self.last_input == BUTTON_BACK:
                    self.post_status = POST_CHOOSE
                    self.should_debounce = True
                    self.keyboard_ran = False
                    self.should_clear_screen = True
                    if keyboard:
                        keyboard.reset()
            else:
                if self.last_input == BUTTON_BACK:
                    self.current_view = SOCIAL_VIEW_MENU
                    self.should_debounce = True
                elif self.last_input in (BUTTON_LEFT, BUTTON_DOWN):
                    if self.post_index > 0:
                        self.post_index -= 1
                        self.should_debounce = True
                elif self.last_input in (BUTTON_RIGHT, BUTTON_UP):
                    if self.post_index < MAX_PRE_SAVED_MESSAGES - 1:
                        self.post_index += 1
                        self.should_debounce = True
                elif self.last_input == BUTTON_CENTER:
                    if self.post_index == 0:
                        self.post_status = POST_KEYBOARD
                        self.should_debounce = True
                        self.keyboard_ran = False
                        self.should_clear_screen = True
                        if keyboard:
                            keyboard.reset()
                    else:
                        selected_post = self.get_selected_post()
                        if selected_post and keyboard:
                            keyboard.response = selected_post
                            self.post_status = POST_KEYBOARD
                            self.should_debounce = True

        elif self.current_view == SOCIAL_VIEW_MESSAGE_USERS:
            if self.last_input == BUTTON_BACK:
                self.current_view = SOCIAL_VIEW_MENU
                self.should_debounce = True
            elif self.last_input in (BUTTON_LEFT, BUTTON_DOWN):
                if self.message_user_index > 0:
                    self.message_user_index -= 1
                    self.should_debounce = True
            elif self.last_input in (BUTTON_RIGHT, BUTTON_UP):
                if self.message_user_index < MAX_MESSAGE_USERS - 1:
                    self.message_user_index += 1
                    self.should_debounce = True
            elif self.last_input == BUTTON_CENTER:
                self.current_view = SOCIAL_VIEW_MESSAGES
                self.should_debounce = True

        elif self.current_view == SOCIAL_VIEW_MESSAGES:
            keyboard = self.view_manager.keyboard
            if self.messages_status == MESSAGES_KEYBOARD:
                if keyboard and keyboard.is_finished:
                    self.keyboard_ran = False
                    self.should_clear_screen = True
                    response = keyboard.response
                    storage = self.view_manager.storage
                    storage.write("picoware/flip_social/message_to_user.txt", response)
                    self.messages_status = MESSAGES_SENDING
                    self.user_request(REQUEST_TYPE_MESSAGE_SEND)
                if self.last_input != -1:
                    self.should_debounce = True
                if self.last_input == BUTTON_BACK:
                    self.messages_status = MESSAGES_SUCCESS
                    self.should_debounce = True
                    self.keyboard_ran = False
                    self.should_clear_screen = True
                    if keyboard:
                        keyboard.reset()
            else:
                if self.last_input == BUTTON_BACK:
                    self.current_view = SOCIAL_VIEW_MESSAGE_USERS
                    self.messages_status = MESSAGES_NOT_STARTED
                    self.messages_index = 0
                    self.should_debounce = True
                elif self.last_input in (BUTTON_LEFT, BUTTON_DOWN):
                    if self.messages_index > 0:
                        self.messages_index -= 1
                        self.should_debounce = True
                elif self.last_input in (BUTTON_RIGHT, BUTTON_UP):
                    if self.messages_index < MAX_MESSAGES - 1:
                        self.messages_index += 1
                        self.should_debounce = True
                elif self.last_input == BUTTON_CENTER:
                    self.messages_status = MESSAGES_KEYBOARD
                    self.should_debounce = True

        elif self.current_view == SOCIAL_VIEW_EXPLORE:
            keyboard = self.view_manager.keyboard
            if self.explore_status == EXPLORE_KEYBOARD_USERS:
                if keyboard and keyboard.is_finished:
                    self.keyboard_ran = False
                    self.should_clear_screen = True
                    response = keyboard.response
                    storage = self.view_manager.storage
                    storage.write("picoware/flip_social/explore_user.txt", response)
                    self.explore_status = EXPLORE_WAITING
                    self.explore_index = 0
                    self.user_request(REQUEST_TYPE_EXPLORE)
                if self.last_input != -1:
                    self.should_debounce = True
                if self.last_input == BUTTON_BACK:
                    self.current_view = SOCIAL_VIEW_MENU
                    self.explore_status = EXPLORE_KEYBOARD_USERS
                    self.explore_index = 0
                    self.should_debounce = True
                    self.keyboard_ran = False
                    self.should_clear_screen = True
                    if keyboard:
                        keyboard.reset()
            elif self.explore_status == EXPLORE_KEYBOARD_MESSAGE:
                if keyboard and keyboard.is_finished:
                    self.keyboard_ran = False
                    self.should_clear_screen = True
                    response = keyboard.response
                    storage = self.view_manager.storage
                    storage.write("picoware/flip_social/message_to_user.txt", response)
                    self.explore_status = EXPLORE_SENDING
                    self.user_request(REQUEST_TYPE_MESSAGE_SEND)
                if self.last_input != -1:
                    self.should_debounce = True
                if self.last_input == BUTTON_BACK:
                    self.explore_status = EXPLORE_SUCCESS
                    self.should_debounce = True
                    self.keyboard_ran = False
                    self.should_clear_screen = True
                    if keyboard:
                        keyboard.reset()
            else:
                if self.last_input == BUTTON_BACK:
                    self.current_view = SOCIAL_VIEW_MENU
                    self.explore_status = EXPLORE_KEYBOARD_USERS
                    self.explore_index = 0
                    self.should_debounce = True
                    self.keyboard_ran = False
                    self.should_clear_screen = True
                    if keyboard:
                        keyboard.reset()
                elif self.last_input in (BUTTON_LEFT, BUTTON_DOWN):
                    if self.explore_index > 0:
                        self.explore_index -= 1
                        self.should_debounce = True
                elif self.last_input in (BUTTON_RIGHT, BUTTON_UP):
                    if self.explore_index < MAX_EXPLORE_USERS - 1:
                        self.explore_index += 1
                        self.should_debounce = True
                elif self.last_input == BUTTON_CENTER:
                    self.explore_status = EXPLORE_KEYBOARD_MESSAGE
                    self.should_debounce = True
                    self.keyboard_ran = False
                    self.should_clear_screen = True
                    if keyboard:
                        keyboard.reset()

        elif self.current_view == SOCIAL_VIEW_PROFILE:
            if self.last_input == BUTTON_BACK:
                self.current_view = SOCIAL_VIEW_MENU
                self.should_debounce = True
            elif self.last_input in (BUTTON_LEFT, BUTTON_DOWN):
                if self.current_profile_element > 0:
                    self.current_profile_element -= 1
                    self.should_debounce = True
            elif self.last_input in (BUTTON_RIGHT, BUTTON_UP):
                if self.current_profile_element < PROFILE_ELEMENT_MAX - 1:
                    self.current_profile_element += 1
                    self.should_debounce = True

        elif self.current_view == SOCIAL_VIEW_COMMENTS:
            keyboard = self.view_manager.keyboard
            if self.comments_status == COMMENTS_KEYBOARD:
                if keyboard and keyboard.is_finished:
                    self.keyboard_ran = False
                    self.should_clear_screen = True
                    response = keyboard.response
                    storage = self.view_manager.storage
                    storage.write("picoware/flip_social/comment_post.txt", response)
                    self.comments_status = COMMENTS_SENDING
                    self.user_request(REQUEST_TYPE_COMMENT_POST)
                if self.last_input != -1:
                    self.should_debounce = True
                if self.last_input == BUTTON_BACK:
                    self.comments_status = COMMENTS_SUCCESS
                    self.should_debounce = True
                    self.keyboard_ran = False
                    self.should_clear_screen = True
                    if keyboard:
                        keyboard.reset()
            else:
                if self.last_input == BUTTON_BACK:
                    self.current_view = SOCIAL_VIEW_FEED
                    self.comment_is_valid = False
                    self.should_debounce = True
                elif self.last_input == BUTTON_LEFT:
                    if self.comments_index > 0:
                        self.comments_index -= 1
                        self.should_debounce = True
                elif self.last_input == BUTTON_RIGHT:
                    if self.comments_index < MAX_COMMENTS - 1:
                        self.comments_index += 1
                        self.should_debounce = True
                elif self.last_input == BUTTON_DOWN:
                    self.comments_status = COMMENTS_KEYBOARD
                    if keyboard:
                        self.keyboard_ran = False
                        self.should_clear_screen = True
                        keyboard.reset()
                        keyboard.response = ""
                    self.should_debounce = True
                elif self.last_input == BUTTON_CENTER:
                    if self.comment_is_valid:
                        self.user_request(REQUEST_TYPE_COMMENT_FLIP)
                    self.should_debounce = True

        elif self.current_view in (
            SOCIAL_VIEW_LOGIN,
            SOCIAL_VIEW_REGISTRATION,
            SOCIAL_VIEW_USER_INFO,
        ):
            if self.last_input == BUTTON_BACK:
                self.current_view = SOCIAL_VIEW_LOGIN
                self.should_return_to_menu = True
                self.should_debounce = True

        self.last_input = -1
