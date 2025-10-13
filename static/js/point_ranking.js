document.querySelectorAll('.username').forEach(el => {
    if(el.textContent.length > 1){
        el.textContent = el.textContent[0] + '**';
    }
});