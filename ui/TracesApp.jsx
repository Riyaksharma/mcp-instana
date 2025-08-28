import { UIResourceRenderer } from '@mcp-ui/client';

function TracesApp({ mcpResponse }) {
  if (!mcpResponse || mcpResponse.type !== 'resource') {
    return <div>No UI resource available.</div>;
  }

  return (
    <UIResourceRenderer
      resource={mcpResponse.resource}
      onUIAction={(result) => {
        console.log('Action:', result);
        return { status: 'handled' };
      }}
    />
  );
}

export default TracesApp;
