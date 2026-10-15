"""TrackingEvent validation: image-specific events must name an image."""

import pytest
from pydantic import ValidationError

from api.models import TrackingEvent


@pytest.mark.parametrize(
    "event_type", ["gallery_click", "lightbox_open", "image_impression", "share_click"]
)
def test_image_events_require_image_id(event_type):
    # Omitting the field must fail too, not only an explicit null
    with pytest.raises(ValidationError):
        TrackingEvent(event_type=event_type)
    with pytest.raises(ValidationError):
        TrackingEvent(event_type=event_type, image_id=None)


@pytest.mark.parametrize("event_type", ["page_view", "scroll_depth", "inquiry_click"])
def test_page_events_allow_no_image_id(event_type):
    assert TrackingEvent(event_type=event_type).image_id is None


def test_share_click_with_image_id():
    event = TrackingEvent(event_type="share_click", image_id=7, metadata='{"method": "copy"}')
    assert event.image_id == 7
