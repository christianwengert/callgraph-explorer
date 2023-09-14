// import hljs from './highlight.min.js';
// const hljs = require('highlight.js');


import hljs from 'https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.8.0/es/highlight.min.js';



window.dash_clientside = Object.assign({}, window.dash_clientside, {
    clientside: {
        hl_code: function(data) {

            const elem = document.getElementById('code');
            // console.log(id, elem)
            const code = hljs.highlight(data.code, {"language": "c++"})
            // console.log(code.value)
            const start = data.start - 1;
            const end = data.end - 1;
            let lines = code.value.split('\n');
            let output = ''
            for (let i = 0; i < lines.length; i++) {
                if (i >= start && i <= end) {
                    output += "<span class='h-line'>"
                }
                output += "<span class='h-linenum'>" + i + "</span>"
                output += lines[i]
                if (i >= start && i <= end) {
                    output += "</span>"
                }
                output += '\n'
            }
            console.log(start, end)

            elem.innerHTML = output



            return {};
        }
    }
});