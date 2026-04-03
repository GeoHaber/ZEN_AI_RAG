use anyhow::{Result, Context};

/// Wait for port.
pub fn wait_for_port(port: String, timeout: String) -> () {
    // Wait for port.
    let mut start_time = std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap().as_secs_f64();
    println!("Waiting for port {}...", port);
    while (std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap().as_secs_f64() - start_time) < timeout {
        let mut sock = socket::socket(socket::AF_INET, socket::SOCK_STREAM);
        {
            let mut result = sock.connect_ex(("127.0.0.1".to_string(), port));
            if result == 0 {
                println!("✅ Port {} is OPEN!", port);
                true
            }
        }
        std::thread::sleep(std::time::Duration::from_secs_f64(1));
        println!("{}", ".".to_string());
    }
    println!("{}", "\n❌ Timeout waiting for port.".to_string());
    false
}
