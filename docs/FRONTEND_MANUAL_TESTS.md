# CoastGuard AI frontend connectivity and mobile checks

These manual checks complement the backend tests. Use synthetic data only. They verify interface behavior, not source authenticity or forecast accuracy.

## Connectivity states

1. Start the API and dashboard with the local setup in the README. Confirm the header reports **Backend connected** and current data is shown only if the API returns eligible advisories.
2. In browser developer tools, enable the Offline network condition (or disable the device network). Confirm the header reports **Device offline**, advisory and source data disappear, and the page explains that reconnecting will trigger a retry.
3. Restore connectivity. Confirm the browser's online event causes an automatic refresh without reloading the page. If the API is still unavailable, the page reports **Backend unavailable** and stays clear of advisory data.
4. Keep the device online and stop the API. Confirm the dashboard reports that the backend cannot be reached, clears the previously displayed advisory data, and offers a retry.
5. Simulate a slow connection with a response delay longer than 10 seconds. Confirm the request ends with **API timed out**, data is cleared, and Retry starts a fresh request.
6. Restart the API and press Retry. Confirm the page recovers and refreshes its last-checked time.

## Mobile and accessibility checks

1. Test at 320px, 375px, and 430px viewport widths and at 200% zoom. Confirm there is no horizontal page scrolling and advisory source, issue, and validity metadata remain readable.
2. Navigate with Tab and Shift+Tab. Confirm links, filters, refresh, retry, and advisory cards have a visible focus indicator and can be activated by keyboard.
3. Confirm common touch controls have at least a 44px target on narrow screens.
4. Enable the operating system or browser reduced-motion preference. Confirm loaders and hover transitions do not animate continuously.
5. Use a screen reader to check that connection changes are announced, error states identify the problem, and the retry button has a clear accessible name.

Record device/browser, viewport, network conditions, and any failures before pilot review. Do not treat this checklist as community usability research; conduct that review with permission and participants from the intended communities.
