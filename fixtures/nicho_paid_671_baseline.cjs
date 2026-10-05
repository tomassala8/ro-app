// Frozen original niche expressions from delivery670 captacion.js; synthetic invocation only.
module.exports=function(cs,k){
    const g = cs.filter(c => c.dinero).reduce((s, c) => s + (c.gasto?.['7d'] || 0), 0), l = cs.reduce((s, c) => s + (c.leads?.['7d'] || 0), 0);
    return { nicho: k, cuentas: cs.length, nombres: cs.map(c => c.nombre).join(', '), leads: l, cpl: cs.some(c => c.dinero) && l ? g / l : null, dinero: cs.some(c => c.dinero) };
};
