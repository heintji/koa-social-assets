import unittest
from unittest.mock import patch
import post_next


class TrialClaimTest(unittest.TestCase):
    def test_old_claim_never_reaches_instagram(self):
        with patch.object(post_next, "post") as post:
            self.assertFalse(post_next.publish({"media": ["https://example.test/a.png"],
                                               "caption": "21 dagen gratis proberen"}))
        post.assert_not_called()


if __name__ == "__main__":
    unittest.main()
