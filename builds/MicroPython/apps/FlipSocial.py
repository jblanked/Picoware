# original from https://github.com/jblanked/FlipSocial
# modified for micropython picoware by @jblanked

from micropython import const
from picoware.system.vector import Vector
from picoware.system.colors import TFT_BLACK, TFT_WHITE

_flip_social_alert = None
_flip_social_app_menu = None
_flip_social_app_index: int = 0  # index for the FlipSocial app menu

_flip_social_run_instance = None

_flip_social_user_is_running: bool = False
_flip_social_user_save_requested: bool = False
_flip_social_user_save_verified: bool = False

_flip_social_password_is_running: bool = False
_flip_social_password_save_requested: bool = False
_flip_social_password_save_verified: bool = False

_flip_social_settings_menu = None

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


class FlipSocialRun:
    """Class to manage the 'Run' view of FlipSocial"""

    def __init__(self, view_manager) -> None:
        from picoware.gui.loading import Loading
        from picoware.system.http import HTTP

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
        self.original_color: int = 0  # original color of the draw instance
        self.post_index: int = 0  # index of the post in the Post submenu
        self.post_status: int = POST_CHOOSE  # current post status
        self.registration_status: int = (
            REGISTRATION_NOT_STARTED  # current registration status
        )
        self.should_debounce: bool = False  # flag to debounce input
        self.should_return_to_menu: bool = False  # flag to return to main menu
        self.user_info_status: int = USER_INFO_NOT_STARTED  # current user info status

        # Private variables to replace bound method attributes
        self.__debounce_counter: int = 0  # debounce counter
        self.__comments_loading_started: bool = False  # comments loading started flag
        self.__explore_loading_started: bool = False  # explore loading started flag
        self.__feed_loading_started: bool = False  # feed loading started flag
        self.__login_loading_started: bool = False  # login loading started flag
        self.__messages_loading_started: bool = False  # messages loading started flag
        self.__message_users_loading_started: bool = (
            False  # message users loading started flag
        )
        self.__post_loading_started: bool = False  # post loading started flag
        self.__registration_loading_started: bool = (
            False  # registration loading started flag
        )
        self.__user_info_loading_started: bool = False  # user info loading started flag

        self.view_manager = view_manager  # reference to view manager

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

    def debounce_input(self) -> None:
        """Debounce input to prevent multiple triggers"""
        if self.should_debounce:
            self.__debounce_counter += 1

            self.last_input = -1

            if self.__debounce_counter < 2:
                return

            self.__debounce_counter = 0
            self.should_debounce = False
            self.input_held = False

    def draw_comments_view(self, canvas) -> None:
        """Draw the comments view"""
        if self.comments_status == COMMENTS_WAITING:
            if not self.__comments_loading_started:
                if not self.loading:
                    from picoware.gui.loading import Loading

                    self.loading = Loading(canvas, TFT_BLACK, TFT_WHITE)
                    self.__comments_loading_started = True
                    if self.loading:
                        self.loading.set_text("Fetching...")
            if not self.http_request_is_finished():
                if self.loading:
                    self.loading.animate(False)
                else:
                    from picoware.gui.loading import Loading

                    self.loading = Loading(canvas, TFT_BLACK, TFT_WHITE)
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
                    self.__comments_loading_started = False
                    return

                self.comments_status = COMMENTS_SUCCESS
                if self.loading:
                    self.loading.stop()
                self.__comments_loading_started = False
        elif self.comments_status == COMMENTS_SUCCESS:
            if self.http and self.http.response:
                response = self.http.response
                if '"comments":[{' in response:
                    try:
                        from ujson import loads

                        obj = loads(response)
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
                                        )

                                        # Draw navigation arrows if there are multiple comments
                                        if self.comments_index > 0:
                                            canvas.text(
                                                Vector(2, 60), "< Prev", TFT_BLACK
                                            )
                                        if self.comments_index < total_comments - 1:
                                            canvas.text(
                                                Vector(96, 60), "Next >", TFT_BLACK
                                            )

                                        # Draw comment counter
                                        counter_text = f"{self.comments_index + 1}/{total_comments}"
                                        canvas.text(
                                            Vector(112, 10), counter_text, TFT_BLACK
                                        )
                                    else:
                                        self.comments_status = COMMENTS_PARSE_ERROR
                                        return
                                else:
                                    # If current comment index doesn't exist, go back to previous
                                    if self.comments_index > 0:
                                        self.comments_index -= 1
                            else:
                                canvas.text(
                                    Vector(0, 10),
                                    "No comments found for this post.",
                                    TFT_BLACK,
                                )
                                canvas.text(
                                    Vector(0, 60), "Be the first, click DOWN", TFT_BLACK
                                )
                    except Exception as e:
                        print(f"Error parsing comments: {e}")
                        self.comments_status = COMMENTS_PARSE_ERROR
                else:
                    canvas.text(
                        Vector(0, 10), "No comments found for this post.", TFT_BLACK
                    )
                    canvas.text(Vector(0, 60), "Be the first, click DOWN", TFT_BLACK)
        elif self.comments_status == COMMENTS_REQUEST_ERROR:
            canvas.text(Vector(0, 10), "Comments request failed!", TFT_BLACK)
            canvas.text(Vector(0, 20), "Check your network and", TFT_BLACK)
            canvas.text(Vector(0, 30), "try again later.", TFT_BLACK)
        elif self.comments_status == COMMENTS_PARSE_ERROR:
            canvas.text(Vector(0, 10), "Failed to parse comments!", TFT_BLACK)
            canvas.text(Vector(0, 20), "Try again...", TFT_BLACK)
        elif self.comments_status == COMMENTS_NOT_STARTED:
            self.comments_status = COMMENTS_WAITING
            self.user_request(REQUEST_TYPE_COMMENT_FETCH)
        elif self.comments_status == COMMENTS_KEYBOARD:
            keyboard = self.view_manager.get_keyboard()
            if keyboard:
                keyboard.run(False, True)
        elif self.comments_status == COMMENTS_SENDING:
            if not self.__comments_loading_started:
                if not self.loading:
                    from picoware.gui.loading import Loading

                    self.loading = Loading(canvas, TFT_BLACK, TFT_WHITE)
                    self.__comments_loading_started = True
                    if self.loading:
                        self.loading.set_text("Sending...")
                else:
                    self.loading.set_text("Sending...")
            if not self.http_request_is_finished():
                if self.loading:
                    self.loading.animate(False)
                else:
                    from picoware.gui.loading import Loading

                    self.loading = Loading(canvas, TFT_BLACK, TFT_WHITE)
            else:
                from picoware.system.http import HTTP_ISSUE

                if self.loading:
                    self.loading.stop()
                self.__comments_loading_started = False

                if not self.http or self.http.state == HTTP_ISSUE:
                    self.comments_status = COMMENTS_REQUEST_ERROR
                    return

                if "[SUCCESS]" in self.http.response:
                    self.current_view = SOCIAL_VIEW_FEED
                    self.current_menu_index = SOCIAL_VIEW_FEED
                    self.comments_status = COMMENTS_NOT_STARTED
                    self.feed_status = FEED_NOT_STARTED
                    self.feed_item_index = 0
                    self.feed_iteration = 1
                else:
                    self.comments_status = COMMENTS_REQUEST_ERROR
        else:
            canvas.text(Vector(0, 10), "Loading comments...", TFT_BLACK)

    def draw_explore_view(self, canvas) -> None:
        """Draw the explore view"""

        if self.explore_status == EXPLORE_WAITING:
            if not self.__explore_loading_started:
                if not self.loading:
                    from picoware.gui.loading import Loading

                    self.loading = Loading(canvas, TFT_BLACK, TFT_WHITE)
                    self.__explore_loading_started = True
                    if self.loading:
                        self.loading.set_text("Fetching...")
                else:
                    self.loading.set_text("Fetching...")
            if not self.http_request_is_finished():
                if self.loading:
                    self.loading.animate(False)
                else:
                    from picoware.gui.loading import Loading

                    self.loading = Loading(canvas, TFT_BLACK, TFT_WHITE)
            else:
                from picoware.system.http import HTTP_ISSUE

                if self.loading:
                    self.loading.stop()

                self.__explore_loading_started = False

                if not self.http or self.http.state == HTTP_ISSUE:
                    self.explore_status = EXPLORE_REQUEST_ERROR
                    return

                response: str = self.http.response

                if response and "users" in response:
                    self.explore_status = EXPLORE_SUCCESS
                    storage = self.view_manager.get_storage()
                    storage.write("picoware/flip_social/explore.json", response)
                    return

                self.explore_status = EXPLORE_REQUEST_ERROR

        elif self.explore_status == EXPLORE_SUCCESS:
            storage = self.view_manager.get_storage()
            data = storage.read("picoware/flip_social/explore.json")
            if data is None:
                canvas.text(Vector(0, 30), "Failed to load explore data.", TFT_BLACK)
                self.explore_status = EXPLORE_PARSE_ERROR
                return
            explore_users = []
            try:
                from ujson import loads

                obj = loads(data)
                if "users" in obj and isinstance(obj["users"], list):
                    explore_users = obj["users"]
            except Exception:
                canvas.text(Vector(0, 30), "Failed to parse explore data.", TFT_BLACK)
                self.explore_status = EXPLORE_PARSE_ERROR
                return
            if not explore_users:
                canvas.text(Vector(0, 30), "No users to explore.", TFT_BLACK)
            else:
                self.draw_menu(canvas, self.explore_index, explore_users)
        elif self.explore_status == EXPLORE_REQUEST_ERROR:
            canvas.text(Vector(0, 10), "Messages request failed!", TFT_BLACK)
            canvas.text(Vector(0, 20), "Check your network and", TFT_BLACK)
            canvas.text(Vector(0, 30), "try again later.", TFT_BLACK)
        elif self.explore_status == EXPLORE_PARSE_ERROR:
            canvas.text(Vector(0, 10), "Error parsing messages!", TFT_BLACK)
            canvas.text(Vector(0, 20), "Try again...", TFT_BLACK)
        elif self.explore_status == EXPLORE_NOT_STARTED:
            self.explore_status = EXPLORE_WAITING
            self.user_request(REQUEST_TYPE_EXPLORE)
        elif self.explore_status == EXPLORE_KEYBOARD_USERS:
            keyboard = self.view_manager.get_keyboard()
            if keyboard:
                keyboard.run(False, True)
        elif self.explore_status == EXPLORE_KEYBOARD_MESSAGE:
            keyboard = self.view_manager.get_keyboard()
            if keyboard:
                keyboard.run(False, True)
        elif self.explore_status == EXPLORE_SENDING:
            if not self.__explore_loading_started:
                if not self.loading:
                    from picoware.gui.loading import Loading

                    self.loading = Loading(canvas, TFT_BLACK, TFT_WHITE)
                    self.__explore_loading_started = True
                    if self.loading:
                        self.loading.set_text("Sending...")
                else:
                    self.loading.set_text("Sending...")
            if not self.http_request_is_finished():
                if self.loading:
                    self.loading.animate(False)
                else:
                    from picoware.gui.loading import Loading

                    self.loading = Loading(canvas, TFT_BLACK, TFT_WHITE)
            else:
                from picoware.system.http import HTTP_ISSUE

                if self.loading:
                    self.loading.stop()
                self.__explore_loading_started = False

                if not self.http or self.http.state == HTTP_ISSUE:
                    self.explore_status = EXPLORE_REQUEST_ERROR
                    return

                if "[SUCCESS]" in self.http.response:
                    self.current_view = SOCIAL_VIEW_MESSAGE_USERS
                    self.current_menu_index = SOCIAL_VIEW_MESSAGE_USERS
                    self.message_users_status = MESSAGE_USERS_NOT_STARTED
                    self.explore_status = EXPLORE_KEYBOARD_USERS
                    self.explore_index = 0
                    keyboard = self.view_manager.get_keyboard()
                    if keyboard:
                        keyboard.reset()
                else:
                    self.explore_status = EXPLORE_REQUEST_ERROR
        else:
            canvas.text(Vector(0, 10), "Retrieving messages...", TFT_BLACK)

    def draw_feed_item(
        self,
        canvas,
        username: str,
        message: str,
        flipped: str,
        flips: str,
        date_created: str,
    ) -> None:
        """Draw a single feed item"""
        is_flipped: bool = flipped == "true"
        flip_count: int = int(flips) if flips.isdigit() else 0
        canvas.text(Vector(0, 18), username, TFT_BLACK)
        self.draw_feed_message(canvas, message, 0, 30)
        flip_message = "flip" if flip_count == 1 else "flips"
        canvas.text(Vector(0, 150), f"{flip_count} {flip_message}", TFT_BLACK)
        flip_status = "Unflip" if is_flipped else "Flip"
        canvas.text(Vector(110 if is_flipped else 115, 150), flip_status, TFT_BLACK)
        if "minutes ago" in date_created:
            canvas.text(Vector(190, 150), date_created, TFT_BLACK)
        else:
            canvas.text(Vector(180, 150), date_created, TFT_BLACK)

    def draw_feed_message(self, canvas, user_message: str, x: int, y: int) -> None:
        """Draw the feed message with wrapping"""
        if not user_message:
            print("drawFeedMessage: No message to draw")
            return

        # Simple word wrapping implementation
        max_width = 320
        line_height = 20
        max_lines = 6
        words = user_message.split()
        lines = []
        current_line = ""

        for word in words:
            test_line = current_line + (" " if current_line else "") + word
            if __string_width(test_line) <= max_width:
                current_line = test_line
            else:
                if current_line:
                    lines.append(current_line)
                    if len(lines) >= max_lines:
                        break
                current_line = word

        if current_line and len(lines) < max_lines:
            lines.append(current_line)

        # Draw each line
        for i, line in enumerate(lines):
            canvas.text(Vector(x, y + (i * line_height)), line, TFT_BLACK)

    def draw_feed_view(self, canvas) -> None:
        """Draw the feed view"""
        if self.feed_status == FEED_WAITING:
            if not self.__feed_loading_started:
                if not self.loading:
                    from picoware.gui.loading import Loading

                    self.loading = Loading(canvas, TFT_BLACK, TFT_WHITE)
                    self.__feed_loading_started = True
                    if self.loading:
                        self.loading.set_text("Fetching...")
                else:
                    self.loading.set_text("Fetching...")
            if not self.http_request_is_finished():
                if self.loading:
                    self.loading.animate(False)
                else:
                    from picoware.gui.loading import Loading

                    self.loading = Loading(canvas, TFT_BLACK, TFT_WHITE)
            else:
                from picoware.system.http import HTTP_ISSUE

                if not self.http or self.http.state == HTTP_ISSUE:
                    self.feed_status = FEED_REQUEST_ERROR
                    if self.loading:
                        self.loading.stop()
                    self.__feed_loading_started = False
                    return

                if self.http.response:
                    self.feed_status = FEED_SUCCESS
                    storage = self.view_manager.get_storage()
                    storage.write("picoware/flip_social/feed.json", self.http.response)
                    if self.loading:
                        self.loading.stop()
                    self.__feed_loading_started = False
                else:
                    self.feed_status = FEED_REQUEST_ERROR

        elif self.feed_status == FEED_SUCCESS:
            storage = self.view_manager.get_storage()
            data = storage.read("picoware/flip_social/feed.json")
            if data:
                try:
                    from ujson import loads

                    obj = loads(data)
                    if "feed" in obj and isinstance(obj["feed"], list):
                        feed_items = obj["feed"]
                        if self.feed_item_index < len(feed_items):
                            item = feed_items[self.feed_item_index]
                            username = item.get("username", "")
                            message = item.get("message", "")
                            flipped = item.get("flipped", "false")
                            flips = str(item.get("flip_count", 0))
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
                                )
                            else:
                                self.feed_status = FEED_PARSE_ERROR
                except Exception as e:
                    print(f"Error parsing feed: {e}")
                    self.feed_status = FEED_PARSE_ERROR

        elif self.feed_status == FEED_REQUEST_ERROR:
            canvas.text(Vector(0, 10), "Feed request failed!", TFT_BLACK)
            canvas.text(Vector(0, 20), "Check your network and", TFT_BLACK)
            canvas.text(Vector(0, 30), "try again later.", TFT_BLACK)

        elif self.feed_status == FEED_PARSE_ERROR:
            canvas.text(Vector(0, 10), "Failed to parse feed!", TFT_BLACK)
            canvas.text(Vector(0, 20), "Try again...", TFT_BLACK)

        elif self.feed_status == FEED_NOT_STARTED:
            self.feed_status = FEED_WAITING
            self.user_request(REQUEST_TYPE_FEED)

        elif self.feed_status == FEED_FLIPPING:
            if not self.__feed_loading_started:
                if not self.loading:
                    from picoware.gui.loading import Loading

                    self.loading = Loading(canvas, TFT_BLACK, TFT_WHITE)
                    self.__feed_loading_started = True
                    if self.loading:
                        self.loading.set_text("Flipping...")
            if not self.http_request_is_finished():
                if self.loading:
                    self.loading.animate(False)
                else:
                    from picoware.gui.loading import Loading

                    self.loading = Loading(canvas, TFT_BLACK, TFT_WHITE)
            else:
                from picoware.system.http import HTTP_ISSUE

                if self.loading:
                    self.loading.stop()
                self.__feed_loading_started = False
                if not self.http or self.http.state == HTTP_ISSUE:
                    self.feed_status = FEED_REQUEST_ERROR
                    return
                if "[SUCCESS]" in self.http.response:
                    # increase the flip count locally for instant feedback
                    # and adjust the flipped status
                    storage = self.view_manager.get_storage()
                    data = storage.read("picoware/flip_social/feed.json")
                    if data:
                        try:
                            from ujson import loads, dumps

                            obj = loads(data)
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
                                    updated_data = dumps(obj)
                                    storage.write(
                                        "picoware/flip_social/feed.json", updated_data
                                    )
                        except Exception as e:
                            print(f"Error updating flip status: {e}")

                    self.feed_status = FEED_SUCCESS
                else:
                    self.feed_status = FEED_REQUEST_ERROR

        else:
            canvas.text(Vector(0, 10), "Loading feed...", TFT_BLACK)

    def draw_login_view(self, canvas) -> None:
        """Draw the login view"""

        if self.login_status == LOGIN_WAITING:
            if not self.__login_loading_started:
                if not self.loading:
                    from picoware.gui.loading import Loading

                    self.loading = Loading(canvas, TFT_BLACK, TFT_WHITE)
                    self.__login_loading_started = True
                    if self.loading:
                        self.loading.set_text("Logging in...")
                else:
                    self.loading.set_text("Logging in...")
            if not self.http_request_is_finished():
                if self.loading:
                    self.loading.animate(False)
            else:
                from picoware.system.http import HTTP_ISSUE

                if self.loading:
                    self.loading.stop()
                self.__login_loading_started = False

                if not self.http or self.http.state == HTTP_ISSUE:
                    self.login_status = LOGIN_REQUEST_ERROR
                    return

                response = self.http.response
                if response:
                    if "[SUCCESS]" in response:
                        self.login_status = LOGIN_SUCCESS
                        self.current_view = SOCIAL_VIEW_MENU
                        storage = self.view_manager.get_storage()
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
            canvas.text(Vector(0, 10), "Login successful!", TFT_BLACK)
            canvas.text(Vector(0, 20), "Press OK to continue.", TFT_BLACK)

        elif self.login_status == LOGIN_CREDENTIALS_MISSING:
            canvas.text(Vector(0, 10), "Missing credentials!", TFT_BLACK)
            canvas.text(Vector(0, 20), "Please set your username", TFT_BLACK)
            canvas.text(Vector(0, 30), "and password in the app.", TFT_BLACK)

        elif self.login_status == LOGIN_REQUEST_ERROR:
            canvas.text(Vector(0, 10), "Login request failed!", TFT_BLACK)
            canvas.text(Vector(0, 20), "Check your network and", TFT_BLACK)
            canvas.text(Vector(0, 30), "try again later.", TFT_BLACK)

        elif self.login_status == LOGIN_WRONG_PASSWORD:
            canvas.text(Vector(0, 10), "Wrong password!", TFT_BLACK)
            canvas.text(Vector(0, 20), "Please check your password", TFT_BLACK)
            canvas.text(Vector(0, 30), "and try again.", TFT_BLACK)

        elif self.login_status == LOGIN_NOT_STARTED:
            self.login_status = LOGIN_WAITING
            self.user_request(REQUEST_TYPE_LOGIN)

        else:
            canvas.text(Vector(0, 10), "Logging in...", TFT_BLACK)

    def draw_main_menu_view(self, canvas) -> None:
        """Draw the main menu view"""
        menu_items = ["Feed", "Post", "Messages", "Explore", "Profile"]
        self.draw_menu(canvas, self.current_menu_index, menu_items)

    def draw_menu(self, canvas, selected_index: int, menu_items: list) -> None:
        """Generic menu drawer"""

        SCREEN_W = 320

        # Draw title
        title = "FlipSocial"
        title_width = __string_width(title)
        title_x = (SCREEN_W - title_width) // 2
        canvas.text(Vector(title_x, 25), title, TFT_BLACK)

        # Draw underline
        canvas.line_custom(
            Vector(title_x, 35), Vector(title_x + title_width, 35), TFT_BLACK
        )

        # Draw decorative pattern
        for i in range(0, SCREEN_W, 10):
            canvas.pixel(Vector(i, 45), TFT_BLACK)

        # Get current item
        if 0 <= selected_index < len(menu_items):
            current_item = menu_items[selected_index]

            menu_y = 100
            box_width = 270
            box_height = 40

            # Draw selection box
            canvas.fill_rectangle(
                Vector(25, menu_y - 30), Vector(box_width, box_height), TFT_BLACK
            )

            # Draw text centered
            item_width = __string_width(current_item)
            item_x = (SCREEN_W - item_width) // 2
            canvas.text(Vector(item_x, menu_y - 10), current_item, TFT_WHITE)

            # Draw navigation arrows
            if selected_index > 0:
                canvas.text(Vector(5, menu_y - 7), "<", TFT_BLACK)
            if selected_index < len(menu_items) - 1:
                canvas.text(Vector(SCREEN_W - 15, menu_y - 7), ">", TFT_BLACK)

            # Draw indicator dots
            indicator_y = 130
            if len(menu_items) <= 15:
                dots_spacing = 15
                dots_start_x = (SCREEN_W - (len(menu_items) * dots_spacing)) // 2
                for i in range(len(menu_items)):
                    dot_x = dots_start_x + (i * dots_spacing)
                    if i == selected_index:
                        canvas.fill_rectangle(
                            Vector(dot_x, indicator_y), Vector(10, 10), TFT_BLACK
                        )
                    else:
                        canvas.rect(
                            Vector(dot_x, indicator_y), Vector(10, 10), TFT_BLACK
                        )

            # Draw decorative bottom pattern
            for i in range(0, SCREEN_W, 10):
                canvas.pixel(Vector(i, 145), TFT_BLACK)

    def draw_messages_view(self, canvas) -> None:
        """Draw the messages view"""

        if self.messages_status == MESSAGES_WAITING:
            if not self.__messages_loading_started:
                if not self.loading:
                    from picoware.gui.loading import Loading

                    self.loading = Loading(canvas, TFT_BLACK, TFT_WHITE)
                    self.__messages_loading_started = True
                    if self.loading:
                        self.loading.set_text("Retrieving...")
                else:
                    self.loading.set_text("Retrieving...")
            if not self.http_request_is_finished():
                if self.loading:
                    self.loading.animate(False)
            else:
                from picoware.system.http import HTTP_ISSUE

                if self.loading:
                    self.loading.stop()
                self.__messages_loading_started = False

                if not self.http or self.http.state == HTTP_ISSUE:
                    self.messages_status = MESSAGES_REQUEST_ERROR
                    return

                if self.http.response and "conversations" in self.http.response:
                    self.messages_status = MESSAGES_SUCCESS
                else:
                    self.messages_status = MESSAGES_REQUEST_ERROR

        elif self.messages_status == MESSAGES_SUCCESS:
            if self.http and self.http.response:
                try:
                    from ujson import loads

                    obj: dict = loads(self.http.response)
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
                                SCREEN_W = 320

                                # Draw title (sender name)
                                title_width = __string_width(sender)
                                title_x = (SCREEN_W - title_width) // 2
                                canvas.text(Vector(title_x, 25), sender, TFT_BLACK)

                                # Draw underline for title
                                canvas.line_custom(
                                    Vector(title_x, 35),
                                    Vector(title_x + title_width, 35),
                                    TFT_BLACK,
                                )

                                # Draw decorative horizontal pattern
                                for i in range(0, SCREEN_W, 10):
                                    canvas.pixel(Vector(i, 45), TFT_BLACK)

                                menu_y = 100

                                # Calculate content lines and box height
                                content_lines = 1
                                if len(content) > 30:
                                    content_lines = 2
                                if len(content) > 60:
                                    content_lines = 3

                                box_height = (content_lines * 20) + 20
                                if box_height < 40:
                                    box_height = 40

                                box_y_offset = -45 if content_lines > 1 else -30

                                # Draw message content box
                                canvas.fill_rectangle(
                                    Vector(25, menu_y + box_y_offset),
                                    Vector(270, box_height),
                                    TFT_BLACK,
                                )

                                # Draw message content with word wrapping
                                if len(content) <= 30:
                                    # Single line
                                    line_width = __string_width(content)
                                    line_x = (SCREEN_W - line_width) // 2
                                    line_y = menu_y + 10 - 20
                                    canvas.text(
                                        Vector(line_x, line_y), content, TFT_WHITE
                                    )
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
                                    line1_width = __string_width(line1)
                                    line1_x = (SCREEN_W - line1_width) // 2
                                    line1_y = menu_y + 10 - 30
                                    canvas.text(
                                        Vector(line1_x, line1_y), line1, TFT_WHITE
                                    )

                                    # Draw second line if it exists
                                    if line2:
                                        line2_width = __string_width(line2)
                                        line2_x = (SCREEN_W - line2_width) // 2
                                        line2_y = menu_y + 10 - 10
                                        canvas.text(
                                            Vector(line2_x, line2_y), line2, TFT_WHITE
                                        )

                                # Navigation arrows
                                if self.messages_index > 0:
                                    canvas.text(Vector(5, menu_y - 7), "<", TFT_BLACK)
                                if self.messages_index < len(convos) - 1:
                                    canvas.text(
                                        Vector(SCREEN_W - 15, menu_y - 7),
                                        ">",
                                        TFT_BLACK,
                                    )

                                # Message counter
                                indicator_y = 130
                                total_messages = len(convos)
                                message_counter = (
                                    f"{self.messages_index + 1}/{total_messages}"
                                )
                                counter_width = __string_width(message_counter)
                                counter_x = (SCREEN_W - counter_width) // 2
                                canvas.text(
                                    Vector(counter_x, indicator_y),
                                    message_counter,
                                    TFT_BLACK,
                                )

                                # Reply indicator
                                reply_text = "Press OK to Reply"
                                reply_width = __string_width(reply_text)
                                reply_x = (SCREEN_W - reply_width) // 2
                                canvas.text(
                                    Vector(reply_x, indicator_y + 25),
                                    reply_text,
                                    TFT_BLACK,
                                )

                                # Draw decorative bottom pattern
                                for i in range(0, SCREEN_W, 10):
                                    canvas.pixel(Vector(i, 145), TFT_BLACK)

                except Exception as e:
                    print(f"Error parsing messages: {e}")
                    self.messages_status = MESSAGES_PARSE_ERROR

        elif self.messages_status == MESSAGES_REQUEST_ERROR:
            canvas.text(Vector(0, 10), "Messages request failed!", TFT_BLACK)
            canvas.text(Vector(0, 20), "Check your network and", TFT_BLACK)
            canvas.text(Vector(0, 30), "try again later.", TFT_BLACK)

        elif self.messages_status == MESSAGES_PARSE_ERROR:
            canvas.text(Vector(0, 10), "Error parsing messages!", TFT_BLACK)
            canvas.text(Vector(0, 20), "Try again...", TFT_BLACK)

        elif self.messages_status == MESSAGES_NOT_STARTED:
            self.messages_status = MESSAGES_WAITING
            self.user_request(REQUEST_TYPE_MESSAGES_WITH_USER)

        elif self.messages_status == MESSAGES_KEYBOARD:
            keyboard = self.view_manager.get_keyboard()
            if keyboard:
                keyboard.run(False, True)

        elif self.messages_status == MESSAGES_SENDING:
            if not self.__messages_loading_started:
                if not self.loading:
                    from picoware.gui.loading import Loading

                    self.loading = Loading(canvas, TFT_BLACK, TFT_WHITE)
                    self.__messages_loading_started = True
                    if self.loading:
                        self.loading.set_text("Sending...")
            if not self.http_request_is_finished():
                if self.loading:
                    self.loading.animate(False)
            else:
                from picoware.system.http import HTTP_ISSUE

                if self.loading:
                    self.loading.stop()
                self.__messages_loading_started = False

                keyboard = self.view_manager.get_keyboard()
                if keyboard:
                    keyboard.reset()

                if not self.http or self.http.state == HTTP_ISSUE:
                    self.messages_status = MESSAGES_REQUEST_ERROR
                    return

                if "[SUCCESS]" in self.http.response:
                    self.messages_status = MESSAGES_NOT_STARTED
                    self.messages_index = 0
                else:
                    self.messages_status = MESSAGES_REQUEST_ERROR

        else:
            canvas.text(Vector(0, 10), "Retrieving messages...", TFT_BLACK)

    def draw_message_users_view(self, canvas) -> None:
        """Draw the message users view"""

        if self.message_users_status == MESSAGE_USERS_WAITING:
            if not self.__message_users_loading_started:
                if not self.loading:
                    from picoware.gui.loading import Loading

                    self.loading = Loading(canvas, TFT_BLACK, TFT_WHITE)
                    self.__message_users_loading_started = True
                    if self.loading:
                        self.loading.set_text("Retrieving...")
                else:
                    self.loading.set_text("Retrieving...")
            if not self.http_request_is_finished():
                if self.loading:
                    self.loading.animate(False)
            else:
                from picoware.system.http import HTTP_ISSUE

                if self.loading:
                    self.loading.stop()
                self.__message_users_loading_started = False

                if not self.http or self.http.state == HTTP_ISSUE:
                    self.message_users_status = MESSAGE_USERS_REQUEST_ERROR
                    return

                response = self.http.response
                if response and "users" in response:
                    self.message_users_status = MESSAGE_USERS_SUCCESS
                    storage = self.view_manager.get_storage()
                    storage.write("picoware/flip_social/message_users.json", response)
                else:
                    self.message_users_status = MESSAGE_USERS_REQUEST_ERROR

        elif self.message_users_status == MESSAGE_USERS_SUCCESS:
            storage = self.view_manager.get_storage()
            data = storage.read("picoware/flip_social/message_users.json")
            if data:
                try:
                    from ujson import loads

                    obj = loads(data)
                    if "users" in obj and isinstance(obj["users"], list):
                        users = obj["users"]
                        if users:
                            self.draw_menu(canvas, self.message_user_index, users)
                        else:
                            canvas.text(Vector(0, 30), "No messages found.", TFT_BLACK)
                except Exception as e:
                    print(f"Error parsing message users: {e}")
                    self.message_users_status = MESSAGE_USERS_PARSE_ERROR
            else:
                canvas.text(Vector(0, 30), "Failed to load messages.", TFT_BLACK)

        elif self.message_users_status == MESSAGE_USERS_REQUEST_ERROR:
            canvas.text(Vector(0, 10), "Messages request failed!", TFT_BLACK)
            canvas.text(Vector(0, 20), "Check your network and", TFT_BLACK)
            canvas.text(Vector(0, 30), "try again later.", TFT_BLACK)

        elif self.message_users_status == MESSAGE_USERS_PARSE_ERROR:
            canvas.text(Vector(0, 10), "Error parsing messages!", TFT_BLACK)
            canvas.text(Vector(0, 20), "Try again...", TFT_BLACK)

        elif self.message_users_status == MESSAGE_USERS_NOT_STARTED:
            self.message_users_status = MESSAGE_USERS_WAITING
            self.user_request(REQUEST_TYPE_MESSAGES_USER_LIST)

        else:
            canvas.text(Vector(0, 10), "Retrieving messages...", TFT_BLACK)

    def draw_post_view(self, canvas) -> None:
        """Draw the post view"""
        if self.post_status == POST_WAITING:
            if not self.__post_loading_started:
                if not self.loading:
                    from picoware.gui.loading import Loading

                    self.loading = Loading(canvas, TFT_BLACK, TFT_WHITE)
                    self.__post_loading_started = True
                    if self.loading:
                        self.loading.set_text("Posting...")
                else:
                    self.loading.set_text("Posting...")
            if not self.http_request_is_finished():
                if self.loading:
                    self.loading.animate(False)
            else:
                from picoware.system.http import HTTP_ISSUE

                if self.loading:
                    self.loading.stop()
                self.__post_loading_started = False

                keyboard = self.view_manager.get_keyboard()
                if keyboard:
                    keyboard.reset()

                if not self.http or self.http.state == HTTP_ISSUE:
                    self.post_status = POST_REQUEST_ERROR
                    return

                if "[SUCCESS]" in self.http.response:
                    self.post_status = POST_SUCCESS
                    self.current_view = SOCIAL_VIEW_FEED
                    self.current_menu_index = SOCIAL_VIEW_FEED
                    self.feed_status = FEED_NOT_STARTED
                    self.feed_iteration = 1
                    self.feed_item_index = 0
                else:
                    self.post_status = POST_REQUEST_ERROR

        elif self.post_status == POST_SUCCESS:
            canvas.text(Vector(0, 10), "Posted successfully!", TFT_BLACK)
            canvas.text(Vector(0, 20), "Press OK to continue.", TFT_BLACK)

        elif self.post_status == POST_REQUEST_ERROR:
            canvas.text(Vector(0, 10), "Post request failed!", TFT_BLACK)
            canvas.text(Vector(0, 20), "Ensure your message", TFT_BLACK)
            canvas.text(Vector(0, 30), "follows the rules.", TFT_BLACK)

        elif self.post_status == POST_PARSE_ERROR:
            canvas.text(Vector(0, 10), "Error parsing post!", TFT_BLACK)
            canvas.text(Vector(0, 20), "Ensure your message", TFT_BLACK)
            canvas.text(Vector(0, 30), "follows the rules.", TFT_BLACK)

        elif self.post_status == POST_KEYBOARD:
            keyboard = self.view_manager.get_keyboard()
            if keyboard:
                keyboard.run(False, True)

        elif self.post_status == POST_CHOOSE:
            storage = self.view_manager.get_storage()
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
            canvas.text(Vector(0, 10), "Awaiting...", TFT_BLACK)

    def draw_profile_view(self, canvas) -> None:
        """Draw the profile view"""

        SCREEN_W = 320
        storage = self.view_manager.get_storage()
        data = storage.read("picoware/flip_social/profile.json")

        if not data:
            canvas.text(
                Vector(SCREEN_W // 2 - 70, 80), "Failed to load user info.", TFT_BLACK
            )
            return

        username = __flip_social_util_get_username(self.view_manager)
        if not username:
            canvas.text(
                Vector(SCREEN_W // 2 - 70, 80), "Failed to load username.", TFT_BLACK
            )
            return

        try:
            from ujson import loads

            obj = loads(data)
            bio = obj.get("bio", "No bio")
            friends_count = str(obj.get("friends_count", 0))
            date_created = obj.get("date_created", "Unknown")

            # Draw title
            title_width = __string_width(username)
            title_x = (SCREEN_W - title_width) // 2
            canvas.text(Vector(title_x, 25), username, TFT_BLACK)

            # Draw underline
            canvas.line_custom(
                Vector(title_x, 35), Vector(title_x + title_width, 35), TFT_BLACK
            )

            # Draw decorative pattern
            for i in range(0, SCREEN_W, 10):
                canvas.pixel(Vector(i, 45), TFT_BLACK)

            # Profile elements
            element_labels = ["Bio", "Friends", "Joined"]
            current_label = element_labels[self.current_profile_element]

            menu_y = 100
            canvas.fill_rectangle(Vector(25, menu_y - 30), Vector(270, 40), TFT_BLACK)

            # Draw content based on current element
            if self.current_profile_element == PROFILE_ELEMENT_BIO:
                content = bio if bio else "No bio"
            elif self.current_profile_element == PROFILE_ELEMENT_FRIENDS:
                content = friends_count
            elif self.current_profile_element == PROFILE_ELEMENT_JOINED:
                content = date_created
            else:
                content = "Unknown"

            content_width = __string_width(content)
            content_x = (SCREEN_W - content_width) // 2
            canvas.text(Vector(content_x, menu_y - 10), content, TFT_WHITE)

            # Navigation arrows
            if self.current_profile_element > 0:
                canvas.text(Vector(5, menu_y - 7), "<", TFT_BLACK)
            if self.current_profile_element < PROFILE_ELEMENT_MAX - 1:
                canvas.text(Vector(SCREEN_W - 15, menu_y - 7), ">", TFT_BLACK)

            # Indicator dots
            indicator_y = 130
            dots_spacing = 15
            dots_start_x = (SCREEN_W - (PROFILE_ELEMENT_MAX * dots_spacing)) // 2
            for i in range(PROFILE_ELEMENT_MAX):
                dot_x = dots_start_x + (i * dots_spacing)
                if i == self.current_profile_element:
                    canvas.fill_rectangle(
                        Vector(dot_x, indicator_y), Vector(8, 8), TFT_BLACK
                    )
                else:
                    canvas.rect(Vector(dot_x, indicator_y), Vector(8, 8), TFT_BLACK)

            # Draw decorative bottom pattern
            for i in range(0, SCREEN_W, 10):
                canvas.pixel(Vector(i, 145), TFT_BLACK)

        except Exception as e:
            print(f"Error parsing profile: {e}")
            canvas.text(Vector(0, 30), "Incomplete profile data.", TFT_BLACK)

    def draw_registration_view(self, canvas) -> None:
        """Draw the registration view"""

        if self.registration_status == REGISTRATION_WAITING:
            if not self.__registration_loading_started:
                if not self.loading:
                    from picoware.gui.loading import Loading

                    self.loading = Loading(canvas, TFT_BLACK, TFT_WHITE)
                    self.__registration_loading_started = True
                    if self.loading:
                        self.loading.set_text("Registering...")
                else:
                    self.loading.set_text("Registering...")
            if not self.http_request_is_finished():
                if self.loading:
                    self.loading.animate(False)
            else:
                from picoware.system.http import HTTP_ISSUE

                if self.loading:
                    self.loading.stop()
                self.__registration_loading_started = False

                if not self.http or self.http.state == HTTP_ISSUE:
                    self.registration_status = REGISTRATION_REQUEST_ERROR
                    return

                response = self.http.response
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
            canvas.text(Vector(0, 10), "Registration successful!", TFT_BLACK)
            canvas.text(Vector(0, 20), "Press OK to continue.", TFT_BLACK)

        elif self.registration_status == REGISTRATION_CREDENTIALS_MISSING:
            canvas.text(Vector(0, 10), "Missing credentials!", TFT_BLACK)
            canvas.text(Vector(0, 20), "Please set your username", TFT_BLACK)
            canvas.text(Vector(0, 30), "and password in the app.", TFT_BLACK)

        elif self.registration_status == REGISTRATION_REQUEST_ERROR:
            canvas.text(Vector(0, 10), "Registration failed!", TFT_BLACK)
            canvas.text(Vector(0, 20), "Check your network and", TFT_BLACK)
            canvas.text(Vector(0, 30), "try again later.", TFT_BLACK)

        else:
            canvas.text(Vector(0, 10), "Registering...", TFT_BLACK)

    def draw_user_info_view(self, canvas) -> None:
        """Draw the user info view"""
        if self.user_info_status == USER_INFO_WAITING:
            if not self.__user_info_loading_started:
                if not self.loading:
                    from picoware.gui.loading import Loading

                    self.loading = Loading(canvas, TFT_BLACK, TFT_WHITE)
                    self.__user_info_loading_started = True
                    if self.loading:
                        self.loading.set_text("Syncing...")
                else:
                    self.loading.set_text("Syncing...")
            if not self.http_request_is_finished():
                if self.loading:
                    self.loading.animate(False)
            else:
                from picoware.system.http import HTTP_ISSUE

                if not self.http or self.http.state == HTTP_ISSUE:
                    self.user_info_status = USER_INFO_REQUEST_ERROR
                    if self.loading:
                        self.loading.stop()
                    self.__user_info_loading_started = False
                    return

                if self.http.response:
                    self.user_info_status = USER_INFO_SUCCESS

                    # Save user info
                    storage = self.view_manager.get_storage()
                    storage.write(
                        "picoware/flip_social/profile.json", self.http.response
                    )

                    if self.loading:
                        self.loading.stop()
                    self.__user_info_loading_started = False
                    self.current_view = SOCIAL_VIEW_PROFILE
                else:
                    self.user_info_status = USER_INFO_REQUEST_ERROR

        elif self.user_info_status == USER_INFO_SUCCESS:
            canvas.text(Vector(0, 10), "User info loaded!", TFT_BLACK)
            canvas.text(Vector(0, 20), "Press OK to continue.", TFT_BLACK)

        elif self.user_info_status == USER_INFO_CREDENTIALS_MISSING:
            canvas.text(Vector(0, 10), "Missing credentials!", TFT_BLACK)
            canvas.text(Vector(0, 20), "Please update your username", TFT_BLACK)
            canvas.text(Vector(0, 30), "and password in settings.", TFT_BLACK)

        elif self.user_info_status == USER_INFO_REQUEST_ERROR:
            canvas.text(Vector(0, 10), "User info request failed!", TFT_BLACK)
            canvas.text(Vector(0, 20), "Check your network and", TFT_BLACK)
            canvas.text(Vector(0, 30), "try again later.", TFT_BLACK)

        elif self.user_info_status == USER_INFO_PARSE_ERROR:
            canvas.text(Vector(0, 10), "Failed to parse user info!", TFT_BLACK)
            canvas.text(Vector(0, 20), "Try again...", TFT_BLACK)

        else:
            canvas.text(Vector(0, 10), "Loading user info...", TFT_BLACK)

    def draw_wrapped_bio(self, canvas, text: str, x: int, y: int) -> None:
        """Draw the bio text with wrapping"""
        if not text or len(text) == 0:
            canvas.text(Vector(64, y + 2), "No bio", TFT_BLACK)
            return

        max_chars_per_line = 18
        text_len = len(text)

        if text_len <= max_chars_per_line:
            canvas.text(Vector(64, y + 2), text, TFT_BLACK)
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

            canvas.text(Vector(x, y), line1, TFT_BLACK)
            canvas.text(Vector(x, y + 8), line2, TFT_BLACK)
        else:
            canvas.text(Vector(x, y), line1, TFT_BLACK)

    def get_message_user(self) -> str:
        """Get the message user at the specified messageUserIndex"""
        storage = self.view_manager.get_storage()
        file_path = (
            "picoware/flip_social/explore.json"
            if self.current_menu_index == SOCIAL_VIEW_EXPLORE
            else "picoware/flip_social/message_users.json"
        )
        data = storage.read(file_path)

        if not data:
            print("Failed to load message user list from storage")
            return ""

        try:
            from ujson import loads

            obj = loads(data)
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
            print(f"Error parsing message user list: {e}")

        return ""

    def get_selected_post(self) -> str:
        """Get the selected post at the specified postIndex"""
        if self.post_index == 0:
            return "[New Post]"

        storage = self.view_manager.get_storage()
        data = storage.read("picoware/flip_social/presaves.txt")

        if not data:
            print("Failed to load pre-saved messages")
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

        self.http = HTTP()

        # Get credentials
        username = __flip_social_util_get_username(self.view_manager)
        password = __flip_social_util_get_password(self.view_manager)

        if not username or not password:
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
            "username": username,
            "password": password,
        }

        # Handle different request types
        storage = self.view_manager.get_storage()

        if request_type == REQUEST_TYPE_LOGIN:
            payload = '{"username":"' + username + '","password":"' + password + '"}'
            if not self.http.post_async(
                "https://www.jblanked.com/flipper/api/user/login/", payload, headers
            ):
                self.login_status = LOGIN_REQUEST_ERROR

        elif request_type == REQUEST_TYPE_REGISTRATION:
            payload = '{"username":"' + username + '","password":"' + password + '"}'
            if not self.http.post_async(
                "https://www.jblanked.com/flipper/api/user/register/", payload, headers
            ):
                self.registration_status = REGISTRATION_REQUEST_ERROR

        elif request_type == REQUEST_TYPE_USER_INFO:
            url = "https://www.jblanked.com/flipper/api/user/profile/" + username + "/"
            if not self.http.get_async(url, headers):
                self.user_info_status = USER_INFO_REQUEST_ERROR

        elif request_type == REQUEST_TYPE_FEED:
            url = (
                "https://www.jblanked.com/flipper/api/feed/"
                + str(MAX_FEED_ITEMS)
                + "/"
                + username
                + "/"
                + str(self.feed_iteration)
                + "/max/series/"
            )
            if not self.http.get_async(url, headers):
                self.feed_status = FEED_REQUEST_ERROR

        elif request_type == REQUEST_TYPE_FLIP_POST:
            payload = {"username": username, "post_id": str(self.feed_item_id)}
            if not self.http.post_async(
                "https://www.jblanked.com/flipper/api/feed/flip/", payload, headers
            ):
                self.feed_status = FEED_REQUEST_ERROR

        elif request_type == REQUEST_TYPE_COMMENT_FETCH:
            self.comment_is_valid = False
            url = (
                "https://www.jblanked.com/flipper/api/feed/comments/"
                + str(MAX_FEED_ITEMS)
                + "/"
                + username
                + "/"
                + str(self.feed_item_id)
                + "/"
            )
            if not self.http.get_async(url, headers):
                self.feed_status = FEED_REQUEST_ERROR

        elif request_type == REQUEST_TYPE_COMMENT_FLIP:
            payload = (
                '{"username":"'
                + username
                + '","post_id":"'
                + str(self.comment_item_id)
                + '"}'
            )
            if not self.http.post_async(
                "https://www.jblanked.com/flipper/api/feed/flip/", payload, headers
            ):
                self.feed_status = FEED_REQUEST_ERROR

        elif request_type == REQUEST_TYPE_MESSAGES_USER_LIST:
            url = (
                "https://www.jblanked.com/flipper/api/messages/"
                + username
                + "/get/list/"
                + str(MAX_MESSAGE_USERS)
                + "/"
            )
            if not self.http.get_async(url, headers):
                self.message_users_status = MESSAGE_USERS_REQUEST_ERROR

        elif request_type == REQUEST_TYPE_MESSAGES_WITH_USER:
            message_user = self.get_message_user()
            if not message_user:
                self.messages_status = MESSAGES_PARSE_ERROR
                return
            url = (
                "https://www.jblanked.com/flipper/api/messages/"
                + username
                + "/get/"
                + message_user
                + "/"
                + str(MAX_MESSAGES)
                + "/"
            )
            if not self.http.get_async(url, headers):
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

            url = "https://www.jblanked.com/flipper/api/messages/" + username + "/post/"
            payload = {"receiver": message_user, "content": message}
            if not self.http.post_async(url, payload, headers):
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
                self.explore_status = EXPLORE_REQUEST_ERROR

        elif request_type == REQUEST_TYPE_POST:
            user_message = storage.read("picoware/flip_social/new_post.txt")
            if not user_message:
                self.post_status = POST_REQUEST_ERROR
                return

            payload = {"username": username, "content": user_message}
            if not self.http.post_async(
                "https://www.jblanked.com/flipper/api/feed/post/", payload, headers
            ):
                self.post_status = POST_REQUEST_ERROR

        elif request_type == REQUEST_TYPE_COMMENT_POST:
            user_comment = storage.read("picoware/flip_social/comment_post.txt")
            if not user_comment:
                self.comments_status = COMMENTS_REQUEST_ERROR
                return

            payload = {
                "username": username,
                "content": user_comment,
                "post_id": str(self.feed_item_id),
            }
            if not self.http.post_async(
                "https://www.jblanked.com/flipper/api/feed/comment/", payload, headers
            ):
                self.comments_status = COMMENTS_REQUEST_ERROR
        else:
            print(f"Unknown request type: {request_type}")
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
        self.original_color = view_manager.get_background_color()
        view_manager.set_background_color(TFT_WHITE)

        # update login status
        storage = view_manager.get_storage()
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
        draw = view_manager.get_draw()
        self.update_draw(draw)
        self.update_input(view_manager.get_input_manager().get_last_button())
        draw.swap()

    def stop(self, view_manager) -> None:
        """Stop the FlipSocial run view"""
        view_manager.set_background_color(self.original_color)

    def update_draw(self, draw) -> None:
        """Update and draw the run view"""
        draw.fill_screen(TFT_WHITE)  # white background
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
            draw.text(Vector(0, 10), "View not implemented", TFT_BLACK)

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

        self.last_input = input_key
        self.debounce_input()

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
                    return
                elif self.current_menu_index == SOCIAL_VIEW_MESSAGE_USERS:
                    self.current_view = SOCIAL_VIEW_MESSAGE_USERS
                    self.should_debounce = True
                    return
                elif self.current_menu_index == SOCIAL_VIEW_EXPLORE:
                    self.current_view = SOCIAL_VIEW_EXPLORE
                    self.should_debounce = True
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
            keyboard = self.view_manager.get_keyboard()
            if self.post_status == POST_KEYBOARD:
                if keyboard and keyboard.is_finished:
                    response = keyboard.get_response()
                    storage = self.view_manager.get_storage()
                    storage.write("picoware/flip_social/new_post.txt", response)
                    self.post_status = POST_WAITING
                    self.user_request(REQUEST_TYPE_POST)
                if self.last_input != -1:
                    self.should_debounce = True
                if self.last_input == BUTTON_BACK:
                    self.post_status = POST_CHOOSE
                    self.should_debounce = True
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
                        if keyboard:
                            keyboard.reset()
                    else:
                        selected_post = self.get_selected_post()
                        if selected_post and keyboard:
                            keyboard.set_response(selected_post)
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
            keyboard = self.view_manager.get_keyboard()
            if self.messages_status == MESSAGES_KEYBOARD:
                if keyboard and keyboard.is_finished:
                    response = keyboard.get_response()
                    storage = self.view_manager.get_storage()
                    storage.write("picoware/flip_social/message_to_user.txt", response)
                    self.messages_status = MESSAGES_SENDING
                    self.user_request(REQUEST_TYPE_MESSAGE_SEND)
                if self.last_input != -1:
                    self.should_debounce = True
                if self.last_input == BUTTON_BACK:
                    self.messages_status = MESSAGES_SUCCESS
                    self.should_debounce = True
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
            keyboard = self.view_manager.get_keyboard()
            if self.explore_status == EXPLORE_KEYBOARD_USERS:
                if keyboard and keyboard.is_finished:
                    response = keyboard.get_response()
                    storage = self.view_manager.get_storage()
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
                    if keyboard:
                        keyboard.reset()
            elif self.explore_status == EXPLORE_KEYBOARD_MESSAGE:
                if keyboard and keyboard.is_finished:
                    response = keyboard.get_response()
                    storage = self.view_manager.get_storage()
                    storage.write("picoware/flip_social/message_to_user.txt", response)
                    self.explore_status = EXPLORE_SENDING
                    self.user_request(REQUEST_TYPE_MESSAGE_SEND)
                if self.last_input != -1:
                    self.should_debounce = True
                if self.last_input == BUTTON_BACK:
                    self.explore_status = EXPLORE_SUCCESS
                    self.should_debounce = True
                    if keyboard:
                        keyboard.reset()
            else:
                if self.last_input == BUTTON_BACK:
                    self.current_view = SOCIAL_VIEW_MENU
                    self.explore_status = EXPLORE_KEYBOARD_USERS
                    self.explore_index = 0
                    self.should_debounce = True
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
            keyboard = self.view_manager.get_keyboard()
            if self.comments_status == COMMENTS_KEYBOARD:
                if keyboard and keyboard.is_finished:
                    response = keyboard.get_response()
                    storage = self.view_manager.get_storage()
                    storage.write("picoware/flip_social/comment_post.txt", response)
                    self.comments_status = COMMENTS_SENDING
                    self.user_request(REQUEST_TYPE_COMMENT_POST)
                if self.last_input != -1:
                    self.should_debounce = True
                if self.last_input == BUTTON_BACK:
                    self.comments_status = COMMENTS_SUCCESS
                    self.should_debounce = True
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
                        keyboard.reset()
                        keyboard.set_response("")
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


def __string_width(text: str) -> int:
    """Calculate the width of a string in pixels"""
    if not text:
        return 0
    return len(text) * 5


def __flip_social_util_get_username(view_manager) -> str:
    """Get the username from storage, or return empty string"""
    storage = view_manager.get_storage()
    data: str = storage.read("picoware/flip_social/username.json")

    if data is not None:
        try:
            from ujson import loads

            obj: dict = loads(data)
            if "username" in obj:
                return obj["username"]
        except Exception:
            pass

    return ""


def __flip_social_util_get_password(view_manager) -> str:
    """Get the password from storage, or return empty string"""
    storage = view_manager.get_storage()
    data: str = storage.read("picoware/flip_social/password.json")

    if data is not None:
        try:
            from ujson import loads

            obj: dict = loads(data)
            if "password" in obj:
                return obj["password"]
        except Exception:
            pass

    return ""


def __flip_social_alert(view_manager, message: str, back: bool = True) -> None:
    """Show an alert"""
    from time import sleep

    global _flip_social_alert

    if _flip_social_alert:
        del _flip_social_alert
        _flip_social_alert = None

    from picoware.gui.alert import Alert

    _flip_social_alert = Alert(
        view_manager.get_draw(),
        message,
        view_manager.get_foreground_color(),
        view_manager.get_background_color(),
    )
    _flip_social_alert.draw("Alert")
    sleep(2)
    if back:
        view_manager.back()


def __flip_social_user_callback(response: str) -> None:
    """Callback for when the user is done entering their username"""
    global _flip_social_user_save_requested

    _flip_social_user_save_requested = True


def __flip_social_user_start(view_manager) -> bool:
    """Start the user view"""
    keyboard = view_manager.get_keyboard()
    if not keyboard:
        return False

    global _flip_social_user_is_running, _flip_social_user_save_requested, _flip_social_user_save_verified

    # reset flags
    _flip_social_user_is_running = True
    _flip_social_user_save_requested = False
    _flip_social_user_save_verified = False

    # Set up save callback that just sets a flag instead of immediately calling back()
    keyboard.on_save_callback = __flip_social_user_callback

    # load the ssid from flash
    keyboard.set_response(__flip_social_util_get_username(view_manager))

    keyboard.run(True, True)

    return True


def __flip_social_user_run(view_manager) -> None:
    """Run the user view"""
    from picoware.system.buttons import BUTTON_BACK

    global _flip_social_user_is_running, _flip_social_user_save_requested, _flip_social_user_save_verified

    if not _flip_social_user_is_running:
        return

    keyboard = view_manager.get_keyboard()
    if not keyboard:
        _flip_social_user_is_running = False
        return

    input_manager = view_manager.get_input_manager()
    input_button = input_manager.get_last_button()

    if input_button == BUTTON_BACK:
        input_manager.reset(True)
        _flip_social_user_is_running = False
        _flip_social_user_save_requested = False
        _flip_social_user_save_verified = False  # don't save
        view_manager.back()
        return

    if _flip_social_user_save_requested:
        input_manager.reset(True)
        _flip_social_user_save_requested = False
        _flip_social_user_is_running = False
        _flip_social_user_save_verified = True  # save
        view_manager.back()
        return

    keyboard.run(True, True)


def __flip_social_user_stop(view_manager) -> None:
    """Stop the user view"""
    from gc import collect

    global _flip_social_user_is_running, _flip_social_user_save_requested, _flip_social_user_save_verified

    keyboard = view_manager.get_keyboard()
    if keyboard:
        # if we need to save, do it now instead of in the callback
        if _flip_social_user_save_verified:
            storage = view_manager.get_storage()
            username = view_manager.get_keyboard().get_response()
            try:
                from ujson import dumps

                obj = {"username": username}
                storage.write("picoware/flip_social/username.json", dumps(obj))
            except Exception:
                pass

        keyboard.reset()

    # reset flags
    _flip_social_user_is_running = False
    _flip_social_user_save_requested = False
    _flip_social_user_save_verified = False

    collect()


def __flip_social_password_callback(response: str) -> None:
    """Callback for when the user is done entering their password"""
    global _flip_social_password_save_requested

    _flip_social_password_save_requested = True


def __flip_social_password_start(view_manager) -> bool:
    """Start the password view"""
    keyboard = view_manager.get_keyboard()
    if not keyboard:
        return False

    global _flip_social_password_is_running, _flip_social_password_save_requested, _flip_social_password_save_verified

    # reset flags
    _flip_social_password_is_running = True
    _flip_social_password_save_requested = False
    _flip_social_password_save_verified = False

    # Set up save callback that just sets a flag instead of immediately calling back()
    keyboard.on_save_callback = __flip_social_password_callback

    # load the password from flash
    keyboard.set_response(__flip_social_util_get_password(view_manager))

    keyboard.run(True, True)

    return True


def __flip_social_password_run(view_manager) -> None:
    """Run the password view"""
    from picoware.system.buttons import BUTTON_BACK

    global _flip_social_password_is_running, _flip_social_password_save_requested, _flip_social_password_save_verified

    if not _flip_social_password_is_running:
        return

    keyboard = view_manager.get_keyboard()
    if not keyboard:
        _flip_social_password_is_running = False
        return

    input_manager = view_manager.get_input_manager()
    input_button = input_manager.get_last_button()

    if input_button == BUTTON_BACK:
        input_manager.reset(True)
        _flip_social_password_is_running = False
        _flip_social_password_save_requested = False
        _flip_social_password_save_verified = False  # don't save
        view_manager.back()
        return

    if _flip_social_password_save_requested:
        input_manager.reset(True)
        _flip_social_password_save_requested = False
        _flip_social_password_is_running = False
        _flip_social_password_save_verified = True  # save
        view_manager.back()
        return

    keyboard.run(True, True)


def __flip_social_password_stop(view_manager) -> None:
    """Stop the password view"""
    from gc import collect

    global _flip_social_password_is_running, _flip_social_password_save_requested, _flip_social_password_save_verified

    keyboard = view_manager.get_keyboard()
    if keyboard:
        # if we need to save, do it now instead of in the callback
        if _flip_social_password_save_verified:
            storage = view_manager.get_storage()
            password = view_manager.get_keyboard().get_response()
            try:
                from ujson import dumps

                obj = {"password": password}
                storage.write("picoware/flip_social/password.json", dumps(obj))
            except Exception:
                pass

        keyboard.reset()

    # reset flags
    _flip_social_password_is_running = False
    _flip_social_password_save_requested = False
    _flip_social_password_save_verified = False

    collect()


def __flip_social_settings_start(view_manager) -> bool:
    """Start the settings view"""
    from picoware.gui.menu import Menu

    global _flip_social_settings_menu

    if _flip_social_settings_menu:
        del _flip_social_settings_menu
        _flip_social_settings_menu = None

    draw = view_manager.get_draw()

    _flip_social_settings_menu = Menu(
        draw,  # draw instance
        "Settings",  # title
        0,  # y
        320,  # height
        view_manager.get_foreground_color(),  # text color
        view_manager.get_background_color(),  # background color
        view_manager.get_selected_color(),  # selected color
        view_manager.get_foreground_color(),  # border/separator color
        2,  # border/separator width
    )

    _flip_social_settings_menu.add_item("Change User")
    _flip_social_settings_menu.add_item("Change Password")

    _flip_social_settings_menu.set_selected(0)
    _flip_social_settings_menu.draw()

    return True


def __flip_social_settings_run(view_manager) -> None:
    """Run the settings view"""
    from picoware.system.buttons import (
        BUTTON_BACK,
        BUTTON_UP,
        BUTTON_DOWN,
        BUTTON_RIGHT,
        BUTTON_CENTER,
    )

    global _flip_social_settings_menu

    input_manager = view_manager.get_input_manager()
    input_button = input_manager.get_last_button()

    if input_button == BUTTON_UP:
        input_manager.reset(True)
        _flip_social_settings_menu.scroll_up()
    elif input_button == BUTTON_DOWN:
        input_manager.reset(True)
        _flip_social_settings_menu.scroll_down()
    elif input_button == BUTTON_BACK:
        input_manager.reset(True)
        view_manager.back()
    elif input_button in (BUTTON_CENTER, BUTTON_RIGHT):
        from picoware.system.view import View

        input_manager.reset(True)
        current_item = _flip_social_settings_menu.get_current_item()

        if current_item == "Change User":
            view_manager.add(
                View(
                    "flip_social_user",
                    __flip_social_user_run,
                    __flip_social_user_start,
                    __flip_social_user_stop,
                )
            )
            view_manager.switch_to("flip_social_user")
        if current_item == "Change Password":
            view_manager.add(
                View(
                    "flip_social_password",
                    __flip_social_password_run,
                    __flip_social_password_start,
                    __flip_social_password_stop,
                )
            )
            view_manager.switch_to("flip_social_password")


def __flip_social_settings_stop(view_manager) -> None:
    """Stop the settings view"""
    from gc import collect

    global _flip_social_settings_menu

    if _flip_social_settings_menu:
        del _flip_social_settings_menu
        _flip_social_settings_menu = None

    collect()


def start(view_manager) -> bool:
    """Start the main app"""
    from picoware.gui.menu import Menu
    
    wifi = view_manager.get_wifi()
    
    # if not a wifi device, return
    if not wifi:
        __flip_social_alert(view_manager, "WiFi not available...", False)
        return False

    # if wifi isn't connected, return
    if not wifi.is_connected():
        from picoware.applications.wifi.utils import connect_to_saved_wifi
        __flip_social_alert(view_manager, "WiFi not connected", False)
        connect_to_save_wifi(view_manager)
        return False

    global _flip_social_app_menu, _flip_social_app_index

    if _flip_social_app_menu:
        del _flip_social_app_menu
        _flip_social_app_menu = None

    view_manager.get_storage().mkdir("picoware/flip_social")

    draw = view_manager.get_draw()

    _flip_social_app_menu = Menu(
        draw,  # draw instance
        "FlipSocial",  # title
        0,  # y
        320,  # height
        view_manager.get_foreground_color(),  # text color
        view_manager.get_background_color(),  # background color
        view_manager.get_selected_color(),  # selected color
        view_manager.get_foreground_color(),  # border/separator color
        2,  # border/separator width
    )

    _flip_social_app_menu.add_item("Run")
    _flip_social_app_menu.add_item("Settings")

    _flip_social_app_menu.set_selected(_flip_social_app_index)
    _flip_social_app_menu.draw()

    return True


def run(view_manager) -> None:
    """Run the main app"""
    from picoware.system.buttons import (
        BUTTON_BACK,
        BUTTON_UP,
        BUTTON_DOWN,
        BUTTON_RIGHT,
        BUTTON_CENTER,
    )

    global _flip_social_app_menu, _flip_social_app_index, _flip_social_run_instance

    input_manager = view_manager.get_input_manager()
    input_button = input_manager.get_last_button()

    if input_button == BUTTON_UP:
        input_manager.reset(True)
        _flip_social_app_menu.scroll_up()
    elif input_button == BUTTON_DOWN:
        input_manager.reset(True)
        _flip_social_app_menu.scroll_down()
    elif input_button == BUTTON_BACK:
        input_manager.reset(True)
        _flip_social_app_index = 0
        view_manager.back()
    elif input_button in (BUTTON_CENTER, BUTTON_RIGHT):
        from picoware.system.view import View

        input_manager.reset(True)
        _flip_social_app_index = _flip_social_app_menu.get_selected_index()
        current_item = _flip_social_app_menu.get_current_item()

        if current_item == "Run":
            if __flip_social_util_get_username(view_manager) == "":
                __flip_social_alert(
                    view_manager,
                    "Please set your username in \nFlipSocial settings first",
                )
                return
            if __flip_social_util_get_password(view_manager) == "":
                __flip_social_alert(
                    view_manager,
                    "Please set your password in \nFlipSocial settings first",
                )
                return

            if _flip_social_run_instance:
                del _flip_social_run_instance
                _flip_social_run_instance = None

            _flip_social_run_instance = FlipSocialRun(view_manager)

            view_manager.add(
                View(
                    "flip_social_run",
                    _flip_social_run_instance.run,
                    _flip_social_run_instance.start,
                    _flip_social_run_instance.stop,
                )
            )
            view_manager.switch_to("flip_social_run")
            return

        if current_item == "Settings":
            view_manager.add(
                View(
                    "flip_social_settings",
                    __flip_social_settings_run,
                    __flip_social_settings_start,
                    __flip_social_settings_stop,
                )
            )
            view_manager.switch_to("flip_social_settings")
            return


def stop(view_manager) -> None:
    """Stop the main app"""
    from gc import collect

    global _flip_social_alert, _flip_social_app_menu, _flip_social_run_instance

    if _flip_social_alert:
        del _flip_social_alert
        _flip_social_alert = None
    if _flip_social_app_menu:
        del _flip_social_app_menu
        _flip_social_app_menu = None
    if _flip_social_run_instance:
        del _flip_social_run_instance
        _flip_social_run_instance = None

    collect()
