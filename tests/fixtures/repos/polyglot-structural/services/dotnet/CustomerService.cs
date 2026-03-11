using System.IO;

namespace Zerantiq.Regintel.Fixtures;

public class CustomerService
{
    public string SaveCustomer(IRepository repo, string email, string payload)
    {
        repo.Execute("INSERT INTO users(email) VALUES (@email)", email);
        File.WriteAllText("customer-export.txt", payload);
        return email;
    }
}
