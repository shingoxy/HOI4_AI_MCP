// Load with node_repl after initializing @oai/sky and selecting exactly one
// returned HOI4 Window as globalThis.targetWindow. Does not launch or activate.
// All app capture/input calls use the supported Computer Use JS API.
globalThis.runGuiPump = async function (durationMs = 45000) {
  const fs = await import('node:fs/promises');
  const endpointPath = nodeRepl.cwd + '/artifacts/phase3a/runtime/endpoint.json';
  const startupDeadline = Date.now() + 5000;
  let endpoint;
  while (!endpoint) {
    try { endpoint = JSON.parse(await fs.readFile(endpointPath, 'utf8')); }
    catch (error) {
      if (error.code !== 'ENOENT' || Date.now() >= startupDeadline) throw error;
      await new Promise(r => setTimeout(r, 100));
    }
  }
  if (!targetWindow || targetWindow.id !== endpoint.hwnd || !/hoi4\.exe$/i.test(targetWindow.app))
    throw Error('Selected Computer Use window does not match attached executor');
  const post = async (path, data) => {
    const response = await fetch(endpoint.url + path, {
      method: 'POST', headers: {'Authorization': 'Bearer ' + endpoint.token,
        'Content-Type': 'application/json'}, body: JSON.stringify(data),
      signal: AbortSignal.timeout(3000)
    });
    const result = await response.json();
    if (!response.ok) throw Error(result.error || 'bridge_error');
    return result;
  };
  const end = Date.now() + Math.min(durationMs, 55000);
  let count = 0;
  while (Date.now() < end) {
    let command;
    try { command = await post('/next', {}); }
    catch (error) {
      nodeRepl.write('Computer Use bridge closed: ' + String(error));
      break;
    }
    if (!command) continue;
    const {id, op, args} = command;
    try {
      await post('/permit', {id});
      let result = null;
      if (op === 'capture') {
        if (!globalThis.guiCaptureReady)
          globalThis.guiState = await sky.get_window_state({window:targetWindow});
        globalThis.guiCaptureReady = false;
        globalThis.targetWindow = guiState.window;
        const screen = guiState.screenshots[0];
        if (!screen || !/^data:image\/(png|jpeg);base64,/.test(screen.url))
          throw Error('Unsupported screenshot format');
        result = {image_base64: screen.url.split(',')[1], screenshot_id:screen.id};
      } else if (op === 'click') {
        if (!guiState || guiState.screenshots[0].id !== args.screenshot_id)
          throw Error('Stale screenshot');
        await post('/permit', {id});
        const observation = guiState;
        globalThis.guiState = null;
        await sky.click({window:observation.window, screenshotId:args.screenshot_id,
          x:args.point[0], y:args.point[1]});
        await new Promise(r => setTimeout(r, 500));
        // Every input refreshes immediately; Python then consumes this state
        // on its next capture without asking a model to interpret the image.
        globalThis.guiState = await sky.get_window_state({window:targetWindow});
        globalThis.targetWindow = guiState.window;
        globalThis.guiCaptureReady = true;
      } else if (op === 'key') {
        if (!['Escape', 'w', 'q', 'y', 'Return'].includes(args.key)) throw Error('Key not allowed');
        if (!globalThis.guiState)
          globalThis.guiState = await sky.get_window_state({window:targetWindow});
        await post('/permit', {id});
        globalThis.guiState = null;
        await sky.press_key({window:targetWindow,key:args.key});
        await new Promise(r => setTimeout(r, 500));
        globalThis.guiState = await sky.get_window_state({window:targetWindow});
        globalThis.targetWindow = guiState.window;
        globalThis.guiCaptureReady = true;
      } else throw Error('Operation not allowed');
      await post('/result', {id, result});
      count++;
    } catch (error) {
      globalThis.guiState = null;
      globalThis.guiCaptureReady = false;
      await post('/result', {id, error:String(error)});
      if (/loss_of_focus|emergency_stop|watchdog|action_timeout/.test(String(error))) break;
    }
  }
  nodeRepl.write(JSON.stringify({computer_use_commands:count}));
};
