<?php
const SST_RATE       = 0.06;   // Sales and Service Tax (6%)
const BATCH_DISCOUNT = 0.50;   // 50% off when using the Batch API
const MAX_USAGE      = 1000000; // upper sanity limit, in M tokens

$models = [
    'gpt5'        => ['name' => 'GPT-5',          'provider' => 'OpenAI',     'price' => 5.00],
    'gpt5mini'    => ['name' => 'GPT-5 Mini',     'provider' => 'OpenAI',     'price' => 0.50],
    'sonnet'      => ['name' => 'Claude Sonnet',  'provider' => 'Anthropic',  'price' => 3.00],
    'haiku'       => ['name' => 'Claude Haiku',   'provider' => 'Anthropic',  'price' => 1.00],
    'geminipro'   => ['name' => 'Gemini Pro',     'provider' => 'Google',     'price' => 2.50],
    'geminiflash' => ['name' => 'Gemini Flash',   'provider' => 'Google',     'price' => 0.30],
    'llama'       => ['name' => 'Llama 70B',      'provider' => 'Meta',       'price' => 0.80],
    'mistral'     => ['name' => 'Mistral Large',  'provider' => 'Mistral AI', 'price' => 2.00],
];

function h($s) { return htmlspecialchars((string)$s, ENT_QUOTES, 'UTF-8'); }
function money($n) { return number_format($n, 2, '.', ','); }

$submitted = ($_SERVER['REQUEST_METHOD'] === 'POST');
$batch     = $submitted && isset($_POST['batch']);
$errors    = [];
$lines     = [];
$subtotal  = 0.0;

if ($submitted) {
    foreach ($models as $key => $m) {
        $raw = isset($_POST['usage'][$key]) && is_string($_POST['usage'][$key])
             ? trim($_POST['usage'][$key]) : '';

        if ($raw === '') { continue; }                       // blank = no usage
        if (!preg_match('/^-?\d+(\.\d+)?$/', $raw)) {
            $errors[] = $m['name'] . ': usage must be a valid number.';
            continue;
        }
        $usage = (float)$raw;
        if ($usage < 0) {
            $errors[] = $m['name'] . ': usage must be a non-negative number.';
            continue;
        }
        if ($usage > MAX_USAGE) {
            $errors[] = $m['name'] . ': usage cannot exceed ' . number_format(MAX_USAGE) . ' M tokens.';
            continue;
        }
        if ($usage > 0) {
            $unit  = $m['price'] * ($batch ? (1 - BATCH_DISCOUNT) : 1);
            $cost  = round($usage * $unit, 2);
            $lines[] = ['name' => $m['name'], 'provider' => $m['provider'],
                        'usage' => $usage, 'unit' => $unit, 'cost' => $cost];
            $subtotal += $cost;
        }
    }
    $subtotal = round($subtotal, 2);
    $sst      = round($subtotal * SST_RATE, 2);
    $total    = round($subtotal + $sst, 2);
}
?>
<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>AI Gateway Dashboard</title>
    <style>
      :root {
        --ink: #17232b; --muted: #5d6b73; --paper: #f4f6f3; --card: #ffffff;
        --line: #d9dfdb; --accent: #0f6b62; --accent-dark: #0a4d46;
        --batch: #b4540a; --danger: #a4262c; --danger-bg: #fbeceb;
      }
      * { box-sizing: border-box; }
      body { margin: 0; background: var(--paper); color: var(--ink);
            font-family: "IBM Plex Sans", "Segoe UI", Roboto, Arial, sans-serif; line-height: 1.5; }
      header { background: var(--ink); color: #fff; padding: 28px 24px; }
      header div, main { max-width: 920px; margin: 0 auto; }
      header h1 { margin: 0 0 4px; font-size: 1.7rem; font-weight: 600; letter-spacing: -0.01em; }
      header p { margin: 0; color: #b9c6cc; }
      main { padding: 24px; }
      section { background: var(--card); border: 1px solid var(--line); border-radius: 10px;
                padding: 24px; margin-bottom: 24px; }
      h2 { margin: 0 0 16px; font-size: 1.15rem; }
      table { width: 100%; border-collapse: collapse; }
      th, td { padding: 10px 12px; text-align: left; border-bottom: 1px solid var(--line); }
      th { font-size: .85rem; color: var(--muted); font-weight: 600; }
      .num { text-align: right; font-variant-numeric: tabular-nums; }
      input[type=text] { width: 130px; padding: 8px 10px; border: 1px solid #aab5ba; border-radius: 6px;
                        font: inherit; text-align: right; }
      input[type=text]:focus, button:focus-visible, .switch input:focus-visible + .track {
        outline: 3px solid #7fc4bb; outline-offset: 1px; }
      .controls { display: flex; flex-wrap: wrap; align-items: center; justify-content: space-between;
                  gap: 16px; margin-top: 20px; }
      .switch { display: inline-flex; align-items: center; gap: 12px; cursor: pointer; font-weight: 500; }
      .switch input { position: absolute; opacity: 0; }
      .track { width: 44px; height: 24px; background: #b7c0c4; border-radius: 12px; position: relative;
              transition: background .15s; }
      .track::after { content: ""; position: absolute; top: 3px; left: 3px; width: 18px; height: 18px;
                      background: #fff; border-radius: 50%; transition: transform .15s; }
      .switch input:checked + .track { background: var(--batch); }
      .switch input:checked + .track::after { transform: translateX(20px); }
      .hint { color: var(--muted); font-weight: 400; font-size: .9rem; }
      button { background: var(--accent); color: #fff; border: 0; border-radius: 6px; padding: 11px 26px;
              font: inherit; font-weight: 600; cursor: pointer; }
      button:hover { background: var(--accent-dark); }
      .error { background: var(--danger-bg); border-left: 4px solid var(--danger); color: var(--danger);
              padding: 14px 18px; border-radius: 6px; margin-bottom: 24px; }
      .error ul { margin: 6px 0 0; padding-left: 20px; }
      .tag { display: inline-block; background: #fbe9d9; color: var(--batch); border-radius: 4px;
            padding: 2px 8px; font-size: .85rem; font-weight: 600; margin-left: 8px; }
      tfoot td { border-bottom: 0; }
      tr.grand td { font-size: 1.25rem; font-weight: 700; border-top: 2px solid var(--ink); }
      .empty { color: var(--muted); }
      @media (max-width: 600px) { th:nth-child(2), td:nth-child(2) { display: none; } input[type=text] { width: 100px; } }
    </style>
  </head>

  <body>
    <header><div>
      <h1>AI Gateway Dashboard</h1>
      <p>Enter your token usage per model to see what this month's bill will be.</p>
    </div></header>

    <main>
    <?php if ($errors): ?>
      <div class="error" id="error-box" role="alert">
        <strong>Fix these entries and calculate again:</strong>
        <ul><?php foreach ($errors as $e): ?><li><?= h($e) ?></li><?php endforeach; ?></ul>
      </div>
    <?php endif; ?>

    <form method="post" action="" id="usage-form" novalidate>
    <section>
      <h2>Available models</h2>
      <table id="model-table">
        <thead><tr>
          <th>Model</th><th>Provider</th><th class="num">Price per 1M tokens</th><th class="num">Usage (M tokens)</th>
        </tr></thead>
        <tbody>
        <?php foreach ($models as $key => $m): ?>
          <tr>
            <td><label for="usage_<?= h($key) ?>"><?= h($m['name']) ?></label></td>
            <td><?= h($m['provider']) ?></td>
            <td class="num">RM<?= money($m['price']) ?></td>
            <td class="num"><input type="text" inputmode="decimal" autocomplete="off" placeholder="0"
                id="usage_<?= h($key) ?>" name="usage[<?= h($key) ?>]"
                value="<?= h($submitted && isset($_POST['usage'][$key]) && is_string($_POST['usage'][$key]) ? $_POST['usage'][$key] : '') ?>"></td>
          </tr>
        <?php endforeach; ?>
        </tbody>
      </table>
      <div class="controls">
        <label class="switch">
          <input type="checkbox" id="batch" name="batch" value="1" <?= $batch ? 'checked' : '' ?>>
          <span class="track"></span>
          <span>Use Batch API <span class="hint">(50% off all prices)</span></span>
        </label>
        <button type="submit" id="calculate">Calculate Usage</button>
      </div>
    </section>
    </form>

    <?php if ($submitted && !$errors): ?>
    <section id="results">
      <h2>Usage summary<?php if ($batch): ?><span class="tag" id="batch-tag">Batch API: 50% off</span><?php endif; ?></h2>
      <?php if ($lines): ?>
      <table id="summary-table">
        <thead><tr><th>Model</th><th class="num">Usage (M tokens)</th><th class="num">Unit price</th><th class="num">Cost</th></tr></thead>
        <tbody>
        <?php foreach ($lines as $l): ?>
          <tr><td><?= h($l['name']) ?> <span class="hint"><?= h($l['provider']) ?></span></td>
              <td class="num"><?= h(rtrim(rtrim(number_format($l['usage'], 6, '.', ','), '0'), '.')) ?></td>
              <td class="num">RM<?= money($l['unit']) ?></td>
              <td class="num">RM<?= money($l['cost']) ?></td></tr>
        <?php endforeach; ?>
        </tbody>
        <tfoot>
          <tr><td colspan="3" class="num">Subtotal</td><td class="num" id="subtotal">RM<?= money($subtotal) ?></td></tr>
          <tr><td colspan="3" class="num">SST (6%)</td><td class="num" id="sst">RM<?= money($sst) ?></td></tr>
          <tr class="grand"><td colspan="3" class="num">Total amount to pay</td><td class="num" id="total">RM<?= money($total) ?></td></tr>
        </tfoot>
      </table>
      <?php else: ?>
      <p class="empty" id="no-usage">No usage entered, so there is nothing to pay.</p>
      <table><tfoot><tr class="grand"><td class="num">Total amount to pay</td><td class="num" id="total">RM<?= money($total) ?></td></tr></tfoot></table>
      <?php endif; ?>
    </section>
    <?php endif; ?>
    </main>
  </body>
</html>
