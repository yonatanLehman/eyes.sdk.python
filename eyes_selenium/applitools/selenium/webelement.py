from __future__ import absolute_import

import math
import typing as tp

from selenium.common.exceptions import WebDriverException
from selenium.webdriver.common.by import By

from applitools.common import logger
from applitools.common.geometry import CoordinatesType, Point, Region
from applitools.common.utils.general_utils import proxy_to

from . import eyes_selenium_utils

if tp.TYPE_CHECKING:
    from typing import Optional, Text
    from selenium.webdriver.remote.webelement import WebElement
    from .positioning import SeleniumPositionProvider
    from .webdriver import EyesWebDriver

_JS_GET_COMPUTED_STYLE_FORMATTED_STR = """
            var elem = arguments[0];
            var styleProp = '%s';
            if (window.getComputedStyle) {
                return window.getComputedStyle(elem, null)
                .getPropertyValue(styleProp);
            } else if (elem.currentStyle) {
                return elem.currentStyle[styleProp];
            } else {
                return null;
            }
    """
_JS_GET_SCROLL_LEFT = "return arguments[0].scrollLeft;"
_JS_GET_SCROLL_TOP = "return arguments[0].scrollTop;"
_JS_GET_SCROLL_WIDTH = "return arguments[0].scrollWidth;"
_JS_GET_SCROLL_HEIGHT = "return arguments[0].scrollHeight;"
_JS_GET_OVERFLOW = "return arguments[0].style.overflow;"
_JS_SET_OVERFLOW_FORMATTED_STR = "arguments[0].style.overflow = '%s'"
_JS_GET_CLIENT_WIDTH = "return arguments[0].clientWidth;"
_JS_GET_CLIENT_HEIGHT = "return arguments[0].clientHeight;"
_JS_SCROLL_TO_FORMATTED_STR = """
        arguments[0].scrollLeft = {:d};
        arguments[0].scrollTop = {:d};
"""
_JS_GET_SCROLL_POSITION = """
return arguments[0].scrollLeft + ';' + arguments[0].scrollTop;
"""
_JS_GET_BORDER_WIDTHS_ARR = """
        var retVal = retVal || [];
        if (window.getComputedStyle) {
        var computedStyle = window.getComputedStyle(elem, null);
        retVal.push(computedStyle.getPropertyValue('border-left-width'));
        retVal.push(computedStyle.getPropertyValue('border-top-width'));
        retVal.push(computedStyle.getPropertyValue('border-right-width'));
        retVal.push(computedStyle.getPropertyValue('border-bottom-width'));
        } else if (elem.currentStyle) {
        retVal.push(elem.currentStyle['border-left-width']);
        retVal.push(elem.currentStyle['border-top-width']);
        retVal.push(elem.currentStyle['border-right-width']);
        retVal.push(elem.currentStyle['border-bottom-width']);
        } else {
        retVal.push(0,0,0,0);
        }
"""
_JS_GET_BORDER_WIDTHS = _JS_GET_BORDER_WIDTHS_ARR + "return retVal;"
_JS_GET_SIZE_AND_BORDER_WIDTHS = """
        var elem = arguments[0];
        var retVal = [arguments[0].clientWidth, arguments[0].clientHeight];
        {}
        return retVal
""".format(
    _JS_GET_BORDER_WIDTHS_ARR
)


@proxy_to(
    "_element",
    [
        "tag_name",
        "text",
        "submit",
        "clear",
        "get_property",
        "get_attribute",
        "is_selected",
        "is_enabled",
        "find_element_by_id",
        "find_elements_by_id",
        "find_element_by_name",
        "find_elements_by_name",
        "find_element_by_link_text",
        "find_elements_by_link_text",
        "find_element_by_partial_link_text",
        "find_elements_by_partial_link_text",
        "find_element_by_tag_name",
        "find_elements_by_tag_name",
        "find_element_by_xpath",
        "find_elements_by_xpath",
        "find_element_by_class_name",
        "find_elements_by_class_name",
        "find_element_by_css_selector",
        "find_elements_by_css_selector",
        "is_displayed",
        "location_once_scrolled_into_view",
        "parent",
        "screenshot_as_base64",
        "screenshot_as_png",
        "screenshot",
        "location_in_view",
        "anonymous_children",
    ],
)
class EyesWebElement(object):
    """
    A wrapper for selenium web element. This enables eyes to be notified
     about actions/events for this element.
    """

    def __init__(self, element, driver):
        # type: (WebElement, EyesWebDriver) -> None
        """
        Ctor.

        :param element: The element in the frame.
        :param eyes: The eyes sdk instance.
        :param driver: EyesWebDriver instance.
        """
        if isinstance(element, EyesWebElement):
            element = element._element
        self._element = element  # type: WebElement
        self._driver = driver  # type: EyesWebDriver

        # setting from outside
        self.position_provider = None  # type: Optional[SeleniumPositionProvider]
        self._original_overflow = None  # type: Optional[Text]

    @property
    def element(self):
        # type: () -> WebElement
        return self._element

    @property
    def driver(self):
        # type: () -> EyesWebDriver
        return self._driver

    @property
    def bounds(self):
        # type: () -> Region
        # noinspection PyUnresolvedReferences
        location = self.location
        left, top = location["x"], location["y"]
        width = height = 0  # Default

        # noinspection PyBroadException
        try:
            size = self._element.size
            width, height = size["width"], size["height"]
        except Exception:
            # Not implemented on all platforms.
            pass
        if left < 0:
            left, width = 0, max(0, width + left)
        if top < 0:
            top, height = 0, max(0, height + top)
        return Region(left, top, width, height, CoordinatesType.CONTEXT_RELATIVE)

    @property
    def location(self):
        return self._element.location

    @property
    def rect(self):
        return self._element.rect

    @property
    def is_attached_to_page(self):
        try:
            self.location
            return True
        except WebDriverException:
            return False

    @property
    def size(self):
        return self._element.size

    @property
    def scroll_location(self):
        # type: () -> Point
        pos = self.driver.execute_script(_JS_GET_SCROLL_POSITION, self.element)
        return eyes_selenium_utils.parse_location_string(pos)

    @property
    def id(self):
        return self._element.id

    def value_of_css_property(self, property_name):
        return self._element.value_of_css_property(property_name)

    def find_element(self, by=By.ID, value=None):
        """
        Returns a WebElement denoted by "By".

        :param by: By which option to search for (default is by ID).
        :param value: The value to search for.
        :return: WebElement denoted by "By".
        """
        # Get result from the original implementation of the underlying driver.
        result = self._original_methods["find_element"](by, value)
        # Wrap the element.
        if result:
            result = EyesWebElement(result, self._driver)
        return result

    def find_elements(self, by=By.ID, value=None):
        """
        Returns a list of web elements denoted by "By".

        :param by: By which option to search for (default is by ID).
        :param value: The value to search for.
        :return: List of web elements denoted by "By".
        """
        # Get result from the original implementation of the underlying driver.
        results = self._original_methods["find_elements"](by, value)
        # Wrap all returned elements.
        if results:
            updated_results = []
            for element in results:
                updated_results.append(EyesWebElement(element, self._driver))
            results = updated_results
        return results

    def click(self):
        """
        Clicks and element.
        """
        self._driver.eyes.add_mouse_trigger_by_element("click", self)
        self._element.click()

    def send_keys(self, *value):
        """
        Sends keys to a certain element.

        :param value: The value to type into the element.
        """
        text = u""
        for val in value:
            if isinstance(val, int):
                val = val.__str__()
            text += val.encode("utf-8").decode("utf-8")
        self._driver.eyes.add_text_trigger_by_element(self, text)
        self._element.send_keys(*value)

    def hide_scrollbars(self):
        # type: () -> tp.Text
        """
        Hides the scrollbars of the current element.

        :return: The previous value of the overflow property (could be None).
        """
        logger.debug("EyesWebElement.hide_scrollbars()")
        self._original_overflow = eyes_selenium_utils.hide_scrollbars(  # type: ignore
            self.driver, self.element
        )
        return self._original_overflow

    def return_to_original_overflow(self):
        return eyes_selenium_utils.return_to_original_overflow(
            self.driver, self.element, self._original_overflow
        )

    def get_computed_style(self, prop_style):
        script = _JS_GET_COMPUTED_STYLE_FORMATTED_STR % prop_style
        return self._driver.execute_script(script, self._element)

    def get_computed_style_int(self, prop_style):

        value = self.get_computed_style(prop_style)
        return int(round(float(value.replace("px", "").strip())))

    def get_scroll_left(self):
        return int(
            math.ceil(self._driver.execute_script(_JS_GET_SCROLL_LEFT, self._element))
        )

    def get_scroll_top(self):
        return math.ceil(self._driver.execute_script(_JS_GET_SCROLL_TOP, self._element))

    def get_scroll_width(self):
        return int(
            math.ceil(self._driver.execute_script(_JS_GET_SCROLL_WIDTH, self._element))
        )

    def get_scroll_height(self):
        return int(
            math.ceil(self._driver.execute_script(_JS_GET_SCROLL_HEIGHT, self._element))
        )

    def get_border_left_width(self):
        return self.get_computed_style_int("border-left-width")

    def get_border_right_width(self):
        return self.get_computed_style_int("border-right-width")

    def get_border_top_width(self):
        return self.get_computed_style_int("border-right-width")

    def get_border_bottom_width(self):
        return self.get_computed_style_int("border-right-width")

    def get_overflow(self):
        return self._driver.execute_script(_JS_GET_OVERFLOW, self._element)

    def get_client_width(self):
        return int(
            math.ceil(
                float(self._driver.execute_script(_JS_GET_CLIENT_WIDTH, self._element))
            )
        )

    def get_client_height(self):
        return int(
            math.ceil(
                float(self._driver.execute_script(_JS_GET_CLIENT_HEIGHT, self._element))
            )
        )

    def scroll_to(self, location):
        # type: (Point) -> Point
        """Scrolls to the specified location inside the element."""
        position = self._driver.execute_script(
            _JS_SCROLL_TO_FORMATTED_STR.format(location["x"], location["y"])
            + _JS_GET_SCROLL_POSITION,
            self._element,
        )
        return eyes_selenium_utils.parse_location_string(position)

    @property
    def size_and_borders(self):
        # type: () -> SizeAndBorders
        ret_val = self._driver.execute_script(
            _JS_GET_SIZE_AND_BORDER_WIDTHS, self._element
        )
        return SizeAndBorders(
            width=int(ret_val[0]),
            height=int(ret_val[1]),
            left=int(ret_val[2].rstrip("px")),
            top=int(ret_val[3].rstrip("px")),
            right=int(ret_val[4].rstrip("px")),
            bottom=int(ret_val[5].rstrip("px")),
        )

    @property
    def bounding_client_rect(self):
        left, top, width, height = self.driver.execute_script(
            "var r = arguments[0].getBoundingClientRect();"
            "return r.left+';'+r.top+';'+r.width+';'+r.height;",
            self._element,
        ).split(";")
        return dict(
            x=math.ceil(float(left)),
            y=math.ceil(float(top)),
            width=math.ceil(float(width)),
            height=math.ceil(float(height)),
        )

    def __str__(self):
        tag_name = "None"
        if self.is_attached_to_page:
            tag_name = self._element.tag_name
        return "EyesWebElement: id {}, tag_name {}".format(self._element.id, tag_name)


class SizeAndBorders(object):
    __slots__ = ("size", "borders")

    def __init__(self, width, height, left, top, right, bottom):
        self.size = dict(width=width, height=height)
        self.borders = dict(left=left, top=top, right=right, bottom=bottom)

    def __str__(self):
        return "SizeAndBorders(size={}, borders={})".format(self.size, self.borders)
