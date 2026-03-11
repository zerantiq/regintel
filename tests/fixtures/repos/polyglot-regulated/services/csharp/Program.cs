var builder = WebApplication.CreateBuilder(args);
var app = builder.Build();

app.MapGet("/privacy/notice", () => "notice at collection");
app.MapPost("/privacy/preferences", () => "service provider opt-out");

app.Run();
