function parseMarkdownToSunburst(md) {
    const lines = md.split('\n');
    let root = { name: "Tema Rapat", children: [] };
    let stack = [ {level: 0, node: root, isHeading: true} ];

    for (let i = 0; i < lines.length; i++) {
        let line = lines[i];
        let trimmed = line.trimStart();
        if (!trimmed) continue;

        let level = 0;
        let text = "";
        let isHeading = false;

        let matchHeader = trimmed.match(/^(#+)\s+(.*)/);
        if (matchHeader) {
            level = matchHeader[1].length;
            text = matchHeader[2];
            isHeading = true;
        } else {
            let matchList = trimmed.match(/^[-*]\s+(.*)/);
            if (matchList) {
                let indentSpaces = line.length - trimmed.length;
                let baseLevel = 1;
                // Cari level heading terakhir sebagai jangkar
                for(let j = stack.length - 1; j >= 0; j--) {
                    if(stack[j].isHeading) {
                        baseLevel = stack[j].level;
                        break;
                    }
                }
                // Bullet level sejajar, kecuali ada indentasi (2 spasi = 1 level sub-bullet)
                level = baseLevel + 1 + Math.floor(indentSpaces / 2);
                text = matchList[1];
            }
        }

        if (!text) continue;
        text = text.replace(/\*\*/g, '').trim();

        // Biarkan parent tanpa 'value', ECharts akan mengakumulasi dari children
        let newNode = { name: text, children: [] };

        while (stack.length > 1 && stack[stack.length - 1].level >= level) {
            stack.pop();
        }

        let parent = stack[stack.length - 1].node;
        parent.children.push(newNode);
        stack.push({ level: level, node: newNode, isHeading: isHeading });
    }

    function assignValues(node) {
        if (node.children.length === 0) {
            node.value = 1; // Hanya leaf node (ujung) yang diberi value
        } else {
            delete node.value;
            node.children.forEach(assignValues);
        }
    }
    assignValues(root);

    return root.children.length > 0 ? root.children : [{name: "Data tidak tersedia", value: 1}];
}
