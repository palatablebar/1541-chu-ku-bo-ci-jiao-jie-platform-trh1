function renderVisual(target, data) {
    const rows = [...data.rows].sort((a,b) => b.estimate - a.estimate).slice(0,7);
    const limit = Math.max(...rows.map(row => row.estimate),1);
    const list = node('div',undefined,'signal-list');
    for (const row of rows) {
        const signal = node('div',undefined,'signal');
        signal.toggleAttribute('data-hold',row.state === '暂停');
        const meter = node('span',undefined,'signal-meter');
        const fill = node('i');
        fill.style.width = `${row.estimate / limit * 100}%`;
        meter.append(fill);
        const ticket = node('button',row.key,'item-link');
        ticket.addEventListener('click',() => inspect(row));
        signal.append(ticket,meter,node('span',`${row.estimate.toFixed(1)} min`));
        list.append(signal);
    }
    target.append(list);
}
