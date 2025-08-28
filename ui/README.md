# MCP Instana UI Integration Guide

This guide explains how to integrate the MCP UI with your Instana MCP backend and render interactive results using the MCP UI React component.

## Overview
- The backend (Python) returns both trace data and a UI resource in the following format:
  ```json
  {
    "traces": { ... },
    "uiResource": { "resource": { ... } }
  }
  ```
- The frontend (React) uses `UIResourceRenderer` to render the UI resource from the backend response.

---

## 1. Backend: Returning MCP UI Resource

In `src/application/application_analyze.py`, the `get_all_traces` tool should return:

```python
return {
    "traces": result_dict,
    "uiResource": {
        "resource": {
            "uri": f"ui://instana/traces?t={int(datetime.utcnow().timestamp())}",
            "mimeType": "text/html",
            "text": htmlString,
        }
    }
}
```

- The UI resource contains HTML to display trace results interactively.

---

## 2. Frontend: Rendering with UIResourceRenderer

A React component (`ui/TracesApp.jsx`) is provided:

```jsx
import { UIResourceRenderer } from '@mcp-ui/client';

function TracesApp({ mcpResponse }) {
  if (!mcpResponse || !mcpResponse.uiResource) {
    return <div>No UI resource available.</div>;
  }
  return (
    <UIResourceRenderer
      resource={mcpResponse.uiResource.resource}
      onUIAction={(result) => {
        console.log('Action:', result);
        return { status: 'handled' };
      }}
    />
  );
}

export default TracesApp;
```

- Pass the backend response to `TracesApp` as the `mcpResponse` prop.
- The UI resource will be rendered interactively.

---

## 3. Example End-to-End Flow

1. **Backend:**
   - Call the `get_all_traces` tool (e.g., via API endpoint).
   - The response includes both trace data and a UI resource.

2. **Frontend:**
   - Fetch the response from the backend.
   - Pass it to `TracesApp`:

```jsx
import TracesApp from './TracesApp';

function MainApp() {
  const [mcpResponse, setMcpResponse] = React.useState(null);

  React.useEffect(() => {
    fetch('/api/get_all_traces')
      .then(res => res.json())
      .then(data => setMcpResponse(data));
  }, []);

  return <TracesApp mcpResponse={mcpResponse} />;
}
```

---

## 4. Requirements
- Install MCP UI packages:
  ```bash
  npm install @mcp-ui/server @mcp-ui/client
  ```
- Ensure your backend endpoint returns the combined response as shown above.
- Use the provided React component to render the UI resource.

---

## 5. Customization
- You can customize the HTML in the UI resource for richer dashboards.
- You can handle user actions via the `onUIAction` callback in `UIResourceRenderer`.

---

## References
- [MCP UI Docs](https://mcpui.dev/)
- [Shopify Engineering Blog](https://shopify.engineering/mcp-ui-breaking-the-text-wall)
- [MCP UI GitHub](https://github.com/idosal/mcp-ui)

---

For questions or further integration help, reach out to the project maintainer.
