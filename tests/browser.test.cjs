const test=require('node:test');const assert=require('node:assert/strict');const net=require('node:net');
const {publicIP,publicURL,startPublicProxy}=require('../apps/desktop/electron/browser.cjs');
test('browser refuses local, special-use and credential URLs',()=>{
  for(const ip of ['127.0.0.1','10.0.0.1','100.100.100.200','192.168.1.1','169.254.169.254','0.0.0.0','224.0.0.1','::1','::ffff:8.8.8.8','fc00::1','2001:db8::1'])assert.equal(publicIP(ip),false,ip);
  for(const ip of ['8.8.8.8','1.1.1.1','2606:4700:4700::1111'])assert.equal(publicIP(ip),true,ip);
  for(const url of ['file:///C:/secret','http://example.com','https://localhost/','https://user:pass@example.com','https://example.com:8080/'])assert.throws(()=>publicURL(url));
});
test('CONNECT proxy rejects private and mixed DNS answers before connecting',async()=>{
  for(const answers of [[{address:'127.0.0.1'}],[{address:'8.8.8.8'},{address:'192.168.1.1'}]]){
    const proxy=await startPublicProxy(async()=>answers);
    try{
      const reply=await new Promise((resolve,reject)=>{const client=net.connect({host:'127.0.0.1',port:proxy.port},()=>client.write('CONNECT example.com:443 HTTP/1.1\r\nHost: example.com:443\r\n\r\n'));let text='';client.on('data',data=>text+=data);client.on('end',()=>resolve(text));client.on('error',reject);});
      assert.match(reply,/403 Forbidden/);
    }finally{proxy.close();}
  }
});
